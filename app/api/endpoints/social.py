"""Social endpoints – follows, groups, posts & reactions."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.gamification import track_progress_and_check_milestones
from app.crud.crud_social import (
    follow as crud_follow,
    group as crud_group,
    group_member as crud_group_member,
    post as crud_post,
    reaction as crud_reaction,
)
from app.schemas.social import (
    FollowResponse,
    FollowStats,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberResponse,
    PostCreate,
    PostUpdate,
    PostResponse,
    ReactionCreate,
    ReactionResponse,
)

router = APIRouter()

# ======================================================================
# FOLLOWS
# ======================================================================


@router.post("/follow/{user_id}", response_model=FollowResponse, status_code=201)
def follow_user(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Follow another user."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    existing = crud_follow.get_follow(db, current_user["id"], user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Already following this user")
    result = crud_follow.create(
        db=db, data={"follower_id": current_user["id"], "following_id": user_id}
    )
    track_progress_and_check_milestones(db, current_user["id"], "follow")
    return result


@router.delete("/follow/{user_id}")
def unfollow_user(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Unfollow a user."""
    success = crud_follow.unfollow(db, current_user["id"], user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not following this user")
    return {"detail": "Unfollowed successfully"}


@router.get("/followers/{user_id}", response_model=List[FollowResponse])
def get_followers(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List a user's followers."""
    return crud_follow.get_followers(db, user_id, skip=skip, limit=limit)


@router.get("/following/{user_id}", response_model=List[FollowResponse])
def get_following(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List the users that *user_id* follows."""
    return crud_follow.get_following(db, user_id, skip=skip, limit=limit)


@router.get("/follow-stats/{user_id}", response_model=FollowStats)
def get_follow_stats(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get follower / following counts for a user."""
    return {
        "followers_count": crud_follow.count_followers(db, user_id),
        "following_count": crud_follow.count_following(db, user_id),
    }


# ======================================================================
# GROUPS
# ======================================================================


@router.post("/groups", response_model=GroupResponse, status_code=201)
def create_group(
    *,
    db: Client = Depends(get_supabase),
    group_in: GroupCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Create a new group (creator is auto-added as admin)."""
    data = group_in.model_dump()
    data["created_by"] = current_user["id"]
    group_row = crud_group.create(db=db, data=data)
    # Add creator as admin
    crud_group_member.create(
        db=db,
        data={
            "group_id": group_row["id"],
            "user_id": current_user["id"],
            "role": "admin",
        },
    )
    group_row["member_count"] = 1
    return group_row


@router.get("/groups", response_model=List[GroupResponse])
def list_groups(
    *,
    db: Client = Depends(get_supabase),
    skip: int = 0,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List public groups."""
    groups = crud_group.get_public_groups(db, skip=skip, limit=limit)
    for g in groups:
        g.setdefault("member_count", 0)
    return groups


@router.get("/groups/mine", response_model=List[GroupResponse])
def list_my_groups(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List groups the current user belongs to."""
    groups = crud_group.get_user_groups(db, current_user["id"])
    for g in groups:
        g.setdefault("member_count", 0)
    return groups


@router.get("/groups/{group_id}", response_model=GroupResponse)
def get_group(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get group details with member count."""
    group_row = crud_group.get_with_member_count(db, id=group_id)
    if not group_row:
        raise HTTPException(status_code=404, detail="Group not found")
    return group_row


@router.put("/groups/{group_id}", response_model=GroupResponse)
def update_group(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    group_in: GroupUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Update a group (creator only)."""
    group_row = crud_group.get(db, id=group_id)
    if not group_row:
        raise HTTPException(status_code=404, detail="Group not found")
    if group_row["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only group creator can update")
    update_data = group_in.model_dump(exclude_unset=True)
    updated = crud_group.update(db=db, id=group_id, data=update_data)
    updated.setdefault("member_count", 0)
    return updated


@router.delete("/groups/{group_id}")
def delete_group(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Delete a group (creator only)."""
    group_row = crud_group.get(db, id=group_id)
    if not group_row:
        raise HTTPException(status_code=404, detail="Group not found")
    if group_row["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only group creator can delete")
    crud_group.remove(db=db, id=group_id)
    return {"detail": "Group deleted"}


@router.post(
    "/groups/{group_id}/join",
    response_model=GroupMemberResponse,
    status_code=201,
)
def join_group(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Join a group."""
    group_row = crud_group.get(db, id=group_id)
    if not group_row:
        raise HTTPException(status_code=404, detail="Group not found")
    # Check existing membership directly
    existing_resp = (
        db.table("group_members")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", current_user["id"])
        .maybe_single()
        .execute()
    )
    if existing_resp.data:
        raise HTTPException(status_code=400, detail="Already a member of this group")
    result = crud_group_member.create(
        db=db,
        data={
            "group_id": group_id,
            "user_id": current_user["id"],
            "role": "member",
        },
    )
    track_progress_and_check_milestones(db, current_user["id"], "join_group")
    return result


@router.delete("/groups/{group_id}/leave")
def leave_group(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Leave a group."""
    resp = (
        db.table("group_members")
        .delete()
        .eq("group_id", group_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Not a member of this group")
    return {"detail": "Left group successfully"}


@router.get("/groups/{group_id}/members", response_model=List[GroupMemberResponse])
def get_group_members(
    *,
    db: Client = Depends(get_supabase),
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """List group members."""
    return crud_group_member.get_multi_by_field(
        db, field="group_id", value=group_id
    )


# ======================================================================
# POSTS & REACTIONS
# ======================================================================


@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(
    *,
    db: Client = Depends(get_supabase),
    post_in: PostCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Create a new post (update, tip, milestone, question)."""
    data = post_in.model_dump()
    data["user_id"] = current_user["id"]
    result = crud_post.create(db=db, data=data)
    result.setdefault("reaction_count", 0)
    track_progress_and_check_milestones(db, current_user["id"], "create_post")
    return result


@router.get("/posts/feed", response_model=List[PostResponse])
def get_feed(
    *,
    db: Client = Depends(get_supabase),
    group_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get the public feed, or a group feed if *group_id* is provided."""
    posts = crud_post.get_feed(db, group_id=group_id, skip=skip, limit=limit)
    for p in posts:
        p.setdefault("reaction_count", 0)
    return posts


@router.get("/posts/mine", response_model=List[PostResponse])
def get_my_posts(
    *,
    db: Client = Depends(get_supabase),
    skip: int = 0,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get the current user's own posts."""
    posts = crud_post.get_user_posts(db, current_user["id"], skip=skip, limit=limit)
    for p in posts:
        p.setdefault("reaction_count", 0)
    return posts


@router.put("/posts/{post_id}", response_model=PostResponse)
def update_post(
    *,
    db: Client = Depends(get_supabase),
    post_id: str,
    post_in: PostUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Update a post (author only)."""
    post_row = crud_post.get(db, id=post_id)
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    if post_row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your post")
    update_data = post_in.model_dump(exclude_unset=True)
    result = crud_post.update(db=db, id=post_id, data=update_data)
    result.setdefault("reaction_count", 0)
    return result


@router.delete("/posts/{post_id}")
def delete_post(
    *,
    db: Client = Depends(get_supabase),
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Delete a post (author only)."""
    post_row = crud_post.get(db, id=post_id)
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    if post_row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your post")
    crud_post.remove(db=db, id=post_id)
    return {"detail": "Post deleted"}


@router.post(
    "/posts/{post_id}/react",
    response_model=ReactionResponse,
    status_code=201,
)
def react_to_post(
    *,
    db: Client = Depends(get_supabase),
    post_id: str,
    reaction_in: ReactionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """React to a post."""
    post_row = crud_post.get(db, id=post_id)
    if not post_row:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud_reaction.create(
        db=db,
        data={
            "post_id": post_id,
            "user_id": current_user["id"],
            "reaction": reaction_in.reaction,
        },
    )


@router.delete("/posts/{post_id}/react")
def remove_reaction(
    *,
    db: Client = Depends(get_supabase),
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Remove your reaction from a post."""
    resp = (
        db.table("post_reactions")
        .delete()
        .eq("post_id", post_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="No reaction to remove")
    return {"detail": "Reaction removed"}
