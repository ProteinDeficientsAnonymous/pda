# Routes (React Router)

| Path | Auth required | Screen |
|------|--------------|--------|
| `/` | No | Landing page |
| `/join` | No | Join request form |
| `/join/success` | No | Success confirmation |
| `/login` | No | Member login |
| `/calendar` | No (member details gated inline) | Community calendar |
| `/events/:id` | No (member details gated inline) | Event detail |
| `/onboarding` | JWT (first login) | Set display name + password |
| `/new-password` | JWT (password reset) | Set new password |
| `/guidelines` | Yes | Community guidelines |
| `/settings` | Yes | Account settings |
| `/events/mine` | Yes | My events |
| `/events/manage` | Yes + manage_events | Manage events |
| `/members` | Yes + manage_users | Members admin |
| `/join-requests` | Yes + approve_join_requests | Join requests |
| `/admin/whatsapp` | Yes + manage_whatsapp | WhatsApp config |
