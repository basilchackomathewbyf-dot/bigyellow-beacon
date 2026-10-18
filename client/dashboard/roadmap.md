# Workflow audit
- [x] Reproduce and repair Learnings loading and slow navigation.
- [x] Check ticket review, replies, AI actions, and learning creation/publishing.
- [x] Check Fleet, Vessels, demo controls, and sign-out for both roles.
- [x] Run regression tests and report remaining limitations.

Verified in demo mode: accept/reject/close, reply, AI rerun/apply, search, learning draft/save/publish/retract, uploaded media after reload, missing-learning recovery, fleet charts and cluster links, vessel list, simulated sync/replies/new reports/reset, sign-out and reviewer access restriction. All 18 tests pass; latest preview build is OK. Real API/AI integration and actual ship delivery remain outside this demo audit because no backend is connected.