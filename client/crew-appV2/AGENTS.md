<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture
- All data goes through `src/api/endpoints/*` (mock when USE_MOCK) and `src/hooks/queries.ts`; components never import mock data — so the real ship API can drop in without UI changes.
- Camera/mic code lives in `src/media/` and runs only in effects/handlers — browser-only APIs break SSR.
- Signed-in screens live under the client-only `_app` layout; Master screens under `_app/master` (role-guarded).
- Sign-in is username + password via `login()` in `src/api/endpoints/auth.ts` (demo accounts in mock mode); sign-out clears the query cache — no pairing/PIN flow.
- Near-miss reporting is one chat-style composer in `src/routes/_app/report.tsx`; photos come only through `AttachMenu` (camera, library, files).
- The 1-5 mood scale (icon + colour tile) lives in `src/lib/moods.ts` and is shared by every check-in surface, so no screen depends on emoji font support.
- Any multi-item CSS grid declares its mobile column count (`grid-cols-1`); a bare `grid` track sizes to max-content and pushes pages wider than the phone.
