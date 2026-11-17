# Appearance not applied + all items in warehouse

## Appearance (cause verified from log lobby_20261107_230655.log:168 and player.json)
- The real newUser request is wrapped: body = {"params": {faceframe, faceicon, faces:"56 ints", name, native, sex, voice}}.
  The handler read req["name"] etc. at top level -> nothing matched -> saved nothing (player.json had created_role_req={"params":..} only,
  name stayed 騎士6038, native/voice/faces56 missing). The newUser reply therefore also echoed defaults.
- Fix (server/handlers.py): _unwrap(req) + _apply_create(); also used by useChangeFaceCard; State.__init__ migrates an old save
  (created_role_req with "params") on the next lobby start. Result now in player.json: name <CHARNAME>, sex 0, native 2, voice 101, faceicon 12, faces56 (56 values).
- auth account / getSelfInfo return faces[:14] (DLL reads 14), faceicon, faceframe, native, voice from player.json (already coded).
- Unknown (hypothesis): whether the lobby 3D model is built from the 14 values or from another route. If still unchanged, check the lobby log for new UNHANDLED routes after login.
## All items
- tools/unlock_all.py: bag is now MERGED (existing/bought rows kept); new option --all-items adds every itemtype row with type 0
  (equipment x1 endurance 100, all others x99). Gift packs (type 1-4, 575 rows) skipped (server would need an open-pack feature).
- Run: unlock_all.py --all-items -> bag 215 -> 1283 rows (+1068). capacity sent = rows+100.
- RISK (older note, guess): a 1283-row bag once "broke the warehouse UI"; if so, rerun without --all-items after restoring the backup.
## Tests
selftest_lobby ALL PASSED (it added 1 bought item row, bag now 1284). Backups: server/data/player.json.bak_20261108_0300 (before),
.bak_20261108_0300_items (after items, before migration), server/data/backups/player_pre_appearance_items.json and player_20261107_234729.json.
