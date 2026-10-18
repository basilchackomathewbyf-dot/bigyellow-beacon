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

## Architecture rules
- All data access goes through `src/api/endpoints/*` (one file per module, `// METHOD /path` comment, mock vs real switched by `USE_MOCK`). UI must never import `src/api/mock`; only endpoints and `endpoints/dev.ts` do. Why: real backend plugs in without UI changes.
- Screens read/write data only via TanStack Query hooks in `src/hooks`, keyed by `src/hooks/query-keys.ts`. Why: consistent caching and invalidation.
- Query reads retain a short freshness window; demo responses avoid artificial network delays, and debounced searches stay disabled until meaningful input. Why: navigation remains quick without removing explicit mutation invalidation or sync polling.
- Demo learning uploads use serializable data URLs rather than temporary object URLs. Why: saved media continues rendering after a page reload; production uploads remain behind the endpoint adapter.
- Pure business rules (transitions, media limits, k≥5 wellbeing) live in `src/lib/rules.ts` and are unit tested. Why: single source of truth for UI and mock.
- Authenticated pages are children of the pathless `_shell` layout (client-side token check). Why: token lives in localStorage.
- Reporter identity must never appear in types, UI, filters or exports.
- All user-facing strings go through i18next (`src/i18n/en.ts`).
- tsconfig keeps `strict` but drops noUncheckedIndexedAccess / exactOptionalPropertyTypes / noPropertyAccessFromIndexSignature. Why: they fight optional search params and partial DTOs without catching real bugs here.
