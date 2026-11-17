# Character creation finish (hang on "loading role resources", appearance not saved)

## Evidence (verified, server\logs\lobby_20261107_222923.log)
- Real newUser request: {faceframe:0, faceicon:12, faces:"0,50,50,..." (56 comma-separated ints), name, native:2 (nation), sex:0, voice:101}.
- Our old reply {code:0, uid} was the last thing; client then sent nothing more (only heartbeats) = stuck on NormalWaiting text 2331322.
- Lua: CreatRoleComeBack (cb 5) nRet 0 does nothing visible; NormalWaiting is hidden by On_Role_Register (cb 8); On_RoleStateUpdate (cb 9) only acts if tutorial<4 (hypothesis).

## Cause (static, hypothesis, schema.py case 13 of PoClientDLL)
newUser RESPONSE parser expects {code, uid, sex, native, voice, name, faces:[int]}. We sent only code+uid, so the DLL got empty role data.

## Fix (server\handlers.py, not yet user-tested)
- new_user stores name/sex/native/voice/faceicon/faceframe and full 56-value list (player.json key faces56), forces tutorialStep >= 5, replies with all parsed fields. Also pushes turorialInfo {msgs:[{tutorial:5}]} after the reply (guess for cb 9; disable with env TK_NEWCHAR_PUSH=0).
- auth account and getSelfInfo now return first 14 faces (DLL reads 14), native, voice from player.json. Appearance on later logins may still not match fully if the 3D face is built from the 56-value list through another route (unknown).
## Test
selftest_lobby ALL PASSED; ad-hoc new_user call OK. player.json restored.
## If still stuck
Send lobby log after newUser: look for new requests/UNHANDLED; try TK_NEWCHAR_PUSH=0.
