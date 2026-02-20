"""P2 Post Service — Feed, CRUD, Like, Report."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage import upload_file
from app.models import Like, Post, PostImage, Report
from app.models.post import PostVisibility, ReportReason
from app.models.user import User
from app.schemas.post import (
    FeedResponse,
    LikeResponse,
    PostAuthorResponse,
    PostImageResponse,
    PostResponse,
    PostUpdateRequest,
)
from app.tasks.image_tasks import process_image


class PostService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    async def get_feed(self, current_user: User, offset: int = 0, limit: int = 20) -> FeedResponse:
        """Return paginated feed: active promotions first, then chronological."""
        visibility_filter = (Post.visibility == PostVisibility.PUBLIC) | (
            Post.couple_id == current_user.couple_id
        )
        base_filter = Post.deleted_at.is_(None) & visibility_filter

        total: int = (
            await self.db.execute(select(func.count(Post.id)).where(base_filter))
        ).scalar_one()

        now = datetime.now(timezone.utc)
        promo_sort = case(
            (and_(Post.is_promoted == True, Post.promoted_until > now), 0),  # noqa: E712
            else_=1,
        )
        stmt = (
            select(Post)
            .options(selectinload(Post.images), selectinload(Post.author))
            .where(base_filter)
            .order_by(promo_sort, Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        posts = list((await self.db.execute(stmt)).scalars().all())

        liked_set = await self._liked_set(current_user.id, [p.id for p in posts])
        return FeedResponse(
            items=[self._to_response(p, liked_set) for p in posts],
            total=total,
            offset=offset,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_post(
        self,
        author: User,
        content: str | None,
        visibility: PostVisibility,
        image_files: list[UploadFile],
    ) -> PostResponse:
        if not content and not image_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post must have content or at least one image",
            )

        post = Post(
            couple_id=author.couple_id,
            author_id=author.id,
            content=content,
            visibility=visibility,
        )
        self.db.add(post)
        await self.db.flush()  # get post.id

        for i, file in enumerate(image_files):
            data = await file.read()
            content_type = file.content_type or "image/jpeg"
            key = f"couples/{author.couple_id}/posts/{post.id}/original_{uuid.uuid4()}.jpg"
            image_url = await upload_file(data, key, content_type)
            self.db.add(PostImage(post_id=post.id, image_url=image_url, sort_order=i))
            # Fire-and-forget image processing (medium + thumbnail)
            process_image.delay(
                source_key=key,
                couple_id=str(author.couple_id),
                post_id=str(post.id),
            )

        await self.db.commit()
        return await self._reload(post.id, set())

    # ------------------------------------------------------------------
    # Get single
    # ------------------------------------------------------------------

    async def get_post(self, post_id: uuid.UUID, current_user: User) -> PostResponse:
        post = await self._get_or_404(post_id)
        self._assert_visible(post, current_user)
        liked_set = await self._liked_set(current_user.id, [post_id])
        return self._to_response(post, liked_set)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_post(
        self, post_id: uuid.UUID, current_user: User, data: PostUpdateRequest
    ) -> PostResponse:
        post = await self._get_or_404(post_id)
        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can edit this post",
            )
        if data.content is not None:
            post.content = data.content
        if data.visibility is not None:
            post.visibility = data.visibility
        await self.db.commit()
        return await self._reload(post_id, set())

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_post(self, post_id: uuid.UUID, current_user: User) -> None:
        post = await self._get_or_404(post_id)
        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can delete this post",
            )
        post.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Like / Unlike
    # ------------------------------------------------------------------

    async def like_post(self, post_id: uuid.UUID, current_user: User) -> LikeResponse:
        post = await self._get_or_404(post_id)
        self._assert_visible(post, current_user)

        existing = (
            await self.db.execute(
                select(Like).where(Like.post_id == post_id, Like.user_id == current_user.id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked")

        self.db.add(Like(post_id=post_id, user_id=current_user.id))
        post.like_count += 1
        await self.db.commit()
        return LikeResponse(liked=True, like_count=post.like_count)

    async def unlike_post(self, post_id: uuid.UUID, current_user: User) -> LikeResponse:
        post = await self._get_or_404(post_id)

        like = (
            await self.db.execute(
                select(Like).where(Like.post_id == post_id, Like.user_id == current_user.id)
            )
        ).scalar_one_or_none()
        if like is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")

        await self.db.delete(like)
        post.like_count = max(0, post.like_count - 1)
        await self.db.commit()
        return LikeResponse(liked=False, like_count=post.like_count)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    async def report_post(
        self,
        post_id: uuid.UUID,
        current_user: User,
        reason: ReportReason,
        description: str | None,
    ) -> None:
        post = await self._get_or_404(post_id)
        self._assert_visible(post, current_user)
        self.db.add(
            Report(
                reporter_id=current_user.id,
                post_id=post_id,
                reason=reason,
                description=description,
            )
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_or_404(self, post_id: uuid.UUID) -> Post:
        stmt = (
            select(Post)
            .options(selectinload(Post.images), selectinload(Post.author))
            .where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        post = (await self.db.execute(stmt)).scalar_one_or_none()
        if post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    async def _reload(self, post_id: uuid.UUID, liked_set: set[uuid.UUID]) -> PostResponse:
        post = await self._get_or_404(post_id)
        return self._to_response(post, liked_set)

    async def _liked_set(self, user_id: uuid.UUID, post_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        if not post_ids:
            return set()
        rows = (
            (
                await self.db.execute(
                    select(Like.post_id).where(Like.post_id.in_(post_ids), Like.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        return set(rows)

    def _assert_visible(self, post: Post, current_user: User) -> None:
        if post.visibility == PostVisibility.PRIVATE and post.couple_id != current_user.couple_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This post is private"
            )

    def _to_response(self, post: Post, liked_set: set[uuid.UUID]) -> PostResponse:
        return PostResponse(
            id=post.id,
            couple_id=post.couple_id,
            author_id=post.author_id,
            author=PostAuthorResponse(
                id=post.author.id,
                display_name=post.author.display_name,
                role=post.author.role.value,
            ),
            content=post.content,
            visibility=post.visibility,
            is_promoted=post.is_promoted,
            promoted_until=post.promoted_until,
            like_count=post.like_count,
            liked_by_me=post.id in liked_set,
            images=[
                PostImageResponse(
                    id=img.id,
                    image_url=img.image_url,
                    thumbnail_url=img.thumbnail_url,
                    sort_order=img.sort_order,
                    width=img.width,
                    height=img.height,
                )
                for img in sorted(post.images, key=lambda x: x.sort_order)
            ],
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
