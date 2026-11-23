# AI GAME STUDIO V5.0 — COMPLETE DEEP-DIVE ARCHITECTURE BIBLE, DUAL-MODE WORKFLOW & NON-STOP MASTER PROMPT

## 1. पूरे प्रोजेक्ट में कौन-सा टूल किस काम आता है? (Complete Tool, Skill & AI Model Registry)

आपके **AI Game Studio V5.0** में हर टूल और AI मॉडल की एक पक्की और अलग जिम्मेदारी तय की गई है ताकि कोई भी टूल आपस में टकराए नहीं और वर्कफ़्लो कभी न अटके:

| क्र. | टूल / मॉडल / स्किल का नाम | स्टेटस | यह आपके स्टूडियो में क्या काम करता है? |
| :--- | :--- | :--- | :--- |
| **1** | **Godot Engine 4.7.2 Stable** ([Godot Releases](https://github.com/godotengine/godot)) | **Core Engine** | `gl_compatibility` रेंडरर, `60Hz` फिजिक्स, 2D/3D सीन, शेडर्स, ऑडियो बस और **Android 16 (Target SDK 36, Min SDK 24)** के साथ Signed APK (`.apk`) और Play Store AAB (`.aab`) बनाता है। |
| **2** | **DeepSeek Harness (`dsh`) + `@ebony-vinyl/dsh-our-free-model@2.8.3`** | **Sole Coding Agent** | पूरे स्टूडियो का **एकमात्र कोडिंग एजेंट** (OpenCode पूरी तरह हटा दिया गया है)। प्राइवेट रिसर्च के लिए यह हमेशा प्राइवेट NVIDIA NIM रूट का इस्तेमाल करता है। |
| **3** | **NVIDIA NIM Starred Coding Models** (`nemotron-3-ultra-550b-a55b`, `nemotron-4-340b-instruct`, `nemotron-3-super-120b-a12b`, `nemotron-3.5-lightning-30b-a3b`, `nemotron-nano-3-30b-a3b`, [Moonshot Kimi K3.1 Pro](https://build.nvidia.com/moonshotai/kimi-k3_1-pro/modelcard)) | **Primary Coding & Architecture** | गेम आर्किटेक्चर, 6 स्टूडियो बाइबल्स, GDScript 4.7.2 कोड जेनरेशन और 3-साइकिल पॉलिश का काम करते हैं (`litellm_config.yaml` और `scripts/dsh_and_skill_executor.py`)। |
| **4** | **Gemini 3.5 Flash Lite (500 RPD) + Gemini 3.1 Flash Lite (500 RPD)** | **Primary Video & Audio QA (1,000 RPD)** | `scripts/multi_video_inspector.py` में सबसे पहले यही दोनों मॉडल आपके चारों रिकॉर्डेड MP4 गेमप्ले वीडियो, ऑडियो और 4-एंगल कैमरा ग्रिड की जाँच करते हैं। |
| **5** | **NVIDIA Starred Omni Model (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`)** | **Backup Multimodal Video/Frame QA** | अगर कभी Gemini API का कोटा खत्म हो या नेटवर्क स्लो हो, तो यह स्टार किया हुआ NVIDIA Omni मॉडल तुरंत वीडियो फ्रेम्स और टेलीमेट्री की जाँच संभाल लेता है। |
| **6** | **Gemini Decision 1 (`gemini-decision-1`)** ([Gemini Decision 1 Docs](https://aistudio.google.com/docs/models/gemini-decision-1)) | **Fast Decision & Rubric Gate (200 RPM, 10K RPD)** | `scripts/gemini_decision_gate.py` में Yes/No पॉलिसी चेक, प्राइवेसी राउटिंग और 0–100 पॉलिश रूब्रिक स्कोरिंग के लिए इस्तेमाल होता है। |
| **7** | **Gemma 4 31B (`gemma-4-31b-it`, 14.4K RPD)** | **High-Volume Text & Code Fallback** | जब भारी टेक्स्ट या कोड रिव्यू की ज़रूरत हो, तो रोज़ाना 14,400 रिक्वेस्ट की लिमिट के साथ बैकअप देता है। |
| **8** | **NVIDIA Reward, Safety & Embed Models** (`nemotron-4-340b-reward`, `nemotron-3.5-content-safety`, `nemotron-3-embed-1b`) | **Quality, Play Store Safety & Search** | पॉलिश स्कोरिंग, Google Play कंटेंट सेफ्टी और रेफरेंस डॉक्युमेंट सर्च के लिए। |
| **9** | **`awesome-gamedev-agent-skills`** ([GitHub](https://github.com/gamedev-skills/awesome-gamedev-agent-skills)) | **Permanent Skill** | गेम फील, कैमरा शेक, ट्वीन एनिमेशन, लेवल बैलेंसिंग और मोबाइल कंट्रोल डिजाइन के नियम सिखाता है। |
| **10** | **`godogen`** ([GitHub](https://github.com/htdt/godogen)) | **Permanent Skill** | Godot 4.7.2 के सीन ट्री (`.tscn`), सिग्नल कनेक्शन और बिना सिंटैक्स एरर के GDScript लिखने के नियम लागू करता है। |
| **11** | **`cloudflare/security-audit-skill`** ([GitHub](https://github.com/cloudflare/security-audit-skill)) | **Permanent Security Skill** | कोड में हार्डकोडेड API कीज़, कमांड इंजेक्शन या असुरक्षित फाइल एक्सेस को पकड़कर ब्लॉक करता है। |
| **12** | **`Jakeschincariol/replica-skill`** (`replica-recon`, `replica-entrepreneur`, `replica-brand`) ([GitHub](https://github.com/Jakeschincariol/replica-skill)) | **Temporary Research & Clean-Room Skill** | रेफरेंस गेम का मैकेनिक्स, **Positive (4-5★) और Negative (1-3★) रिव्यू** पढ़कर यूनिक फीचर्स निकालता है और ट्रेडमार्क सुरक्षा सुनिश्चित करता है। |
| **13** | **`storytold/craft-anything`** ([GitHub](https://github.com/storytold/craft-anything)) | **Temporary UI/Screen Study Skill** | स्क्रीनशॉट्स और UI फ्लो से सभी 12 स्क्रीन्स और बटन लेआउट का सटीक मैप (`docs/UI_ELEMENT_AND_INTERACTION_MAP.json`) बनाने में मदद करता है। |
| **14** | **`morluto/rea` (`rea-agents`)** ([GitHub](https://github.com/morluto/rea)) | **Standby Reverse-Engineering Tool** | डिफ़ॉल्ट रूप से `STANDBY_DORMANT` रहता है; जब आप `ORDER.md` में `USE_REA: true` लिखते हैं, तब लीगल APK के बाइनरी/लेआउट स्ट्रक्चर का गहरा विश्लेषण करता है। |
| **15** | **`Xvfb` (`2560x2560x24`) + `llvmpipe` OpenGL3 + `PulseAudio` + `FFmpeg` + `ImageMagick`** | **Virtual Screen & Movie Maker** | बिना फिजिकल मॉनिटर वाले GitHub सर्वर पर वर्चुअल स्क्रीन और वर्चुअल साउंड कार्ड बनाता है ताकि Godot का `--write-movie` (Movie Maker) पूरा 3D/2D गेम और ऑडियो रिकॉर्ड कर सके। |
| **16** | **OpenSSL AES-256-CBC (`-pbkdf2 -iter 100000`) + `keytool` + `apksigner`** | **Keystore & APK/AAB Security** | आपके Play Store Keystore को एन्क्रिप्ट करके प्राइवेट Hugging Face Vault में रखता है और APK/AAB के डिजिटल सिग्नेचर की जाँच करता है। |

---

## 2. आपके गेम बनने के दोनों रास्ते (Dual-Mode Game Creation Architecture)

आपका स्टूडियो (`scripts/dual_mode_game_factory.py` + `scripts/hf_vault_sync.py`) **दोनों तरीकों** से अपने-आप गेम बनाता है और कभी नहीं अटकता:

### रास्ता A: Play Store लिंक या APK से नया ओरिजिनल गेम बनाना (`PATH_A_REFERENCE_LINK_OR_APK`)
जब आप `ORDER.md` में `PLAYSTORE_REFERENCE_LINK:` (जैसे [`https://play.google.com/store/apps/details?id=com.block.juggle`](https://play.google.com/store/apps/details?id=com.block.juggle)), `REFERENCE_APK_URL:` (25MB से बड़े APK के लिए सीधा क्लाउड लिंक), या `MY_RESEARCH_AND_FILES/` में कोई `.apk` देते हैं:
1. **Deep Reference & APK Inspection (`deep_game_intelligence.py`, `playstore_cleanroom_recon.py`, `apk_and_source_archaeologist.py`)**:
   - गेम का जॉनर, इंजन, कोर गेमप्ले लूप (जैसे 8x8 बोर्ड, 3-पीस ट्रे, Juggle Hold स्लॉट, लाइन-क्लियर कॉम्बो गणित), कठिनता का ग्राफ (Level 1 से 30) और कलर वेट्स निकालता है।
   - हर स्क्रीन और बटन की पोज़िशन, साइज (`>=56px`) और नेविगेशन मैप (`docs/UI_ELEMENT_AND_INTERACTION_MAP.json`) तैयार करता है।
   - **Ad और IAP प्राइसिंग ब्लूप्रिंट**: कौन-सा Ad कब दिखेगा (Rewarded Revive, Rewarded 2x Coins, और Level >= 3 के बाद 180 सेकंड कूलडाउन वाला Interstitial Ad) और हर IAP आइटम की कीमत (`₹89 / $0.99 Starter Pack`, `₹249 / $2.99 Remove Ads Forever`, `₹169` से `₹849` कॉइन और बूस्टर पैक) सेट करता है।
2. **Positive + Negative Review Analysis & Unique Upgrade Injection (`scripts/review_intelligence.py`)**:
   - रेफरेंस गेम के **4–5 स्टार पॉजिटिव रिव्यू** पढ़ता है ताकि जो चीज़ें खिलाड़ियों को सबसे ज़्यादा पसंद हैं (जैसे स्मूथ पीस प्लेसमेंट और मल्टी-लाइन कॉम्बो फील) उन्हें 100% बरकरार रखा जाए।
   - साथ ही **1–3 स्टार नेगेटिव रिव्यू** पढ़ता है और कमियों को दूर करने के लिए आपके गेम में **3 नए यूनिक फीचर्स** (`docs/UNIQUE_GAME_UPGRADE_SPEC.json`) अपने-आप जोड़ता है:
     - **`Smart Mercy & Juggle Vault`**: जब बोर्ड पर जगह कम हो (`< 2` मूव्स), तो 3x3 देकर हराने के बजाय गारंटीड रेस्क्यू पीस (`1x1` या `1x2`) और Juggle Hold स्लॉट देता है।
     - **`Crystal Fever Overdrive Mode`**: लगातार `3x+` कॉम्बो बनने पर **Fever Overdrive** चालू होता है जो दोगुने पॉइंट्स देता है और बोर्ड के सभी 4-हिट आर्मर्ड क्रिस्टल ब्लॉक्स की 1 HP तोड़ देता है।
     - **`Streak Booster Forge`**: हर 5 लेवल पार करने पर मुफ्त Hammer Smash और Juggle Swap बूस्टर देता है और गेम के बीच में कभी जबरन Ad नहीं दिखाता।
3. **100% Copyright-Safe Original Asset Generation (`scripts/original_asset_factory.py` + Godot Movie Maker / Procedural 3D & 2D)**:
   - किसी दूसरे APK की फाइलों का हैश बदलने के बजाय (जिससे Google Play अकाउंट बैन हो सकता है), स्टूडियो रेफरेंस गेम के साइज और कलर हार्मनी के आधार पर Godot 4.7.2 के अंदर **100% ओरिजिनल 3D/2D बेवल्ड मेश, `clearcoat=0.9` ग्लॉसी शेडर्स, कस्टम SVG आइकन्स और 44.1kHz WAV साउंड इफेक्ट्स** खुद बनाता है।

### रास्ता B: सिर्फ़ आपके अपने आइडिया और रिसर्च नोट्स से गेम बनाना (`PATH_B_USER_ORIGINAL_IDEA`)
जब आप `PLAYSTORE_REFERENCE_LINK:` को खाली रखते हैं और `ORDER.md` के `## PROMPT:` में अपना आइडिया लिखते हैं (या `MY_RESEARCH_AND_FILES/` में अपने `.md`, `.pdf`, `.txt` रिसर्च नोट्स और एसेट्स डालते हैं):
1. `dual_mode_game_factory.py` तुरंत `PATH_B_USER_ORIGINAL_IDEA` मोड चालू करता है।
2. आपके प्रॉम्प्ट और PDF/Markdown नोट्स को मिलाकर `docs/COMBINED_USER_RESEARCH.md` बनाता है।
3. `generate_complete_game_bible.py` आपके आइडिया के हिसाब से 6 स्टूडियो बाइबल्स (`COMPLETE_GAME_BIBLE.md`, `UI_UX_BIBLE.md`, `MECHANICS_CONTRACT.md`, `TECHNICAL_ARCHITECTURE.md`, `ART_DIRECTION_BIBLE.md`, `REFERENCE_INTELLIGENCE_DOSSIER.md`) तैयार करता है।
4. जॉनर (`block_puzzle`, `bubble_shooter`, `racing_3d`, `endless_runner`) और कैटेगरी (`level_by_level` में 30 लेवल्स या `endless_map_chunks` में 5 सीमलेस मैप चंक्स) के अनुसार पूरा गेम, 12 स्क्रीन्स, ऑडियो और मोनेटाइजेशन तैयार करता है।

---

## 3. स्टूडियो-लेवल पॉलिश (Studio-Level Polish) और 4-Video QA कैसे काम करता है?

1. **3-Cycle Studio Polish Loop (`scripts/studio_polish_director.py`)**:
   - **Cycle 1 (Visuals & Shaders)**: `WorldEnvironment` ग्लो, `DirectionalLight3D` शैडो (`shadow_enabled = true`), `clearcoat_enabled = true` (`0.9`) और एमिसिव हाइलाइट्स लगाता है।
   - **Cycle 2 (UI/UX, Tween & Particles)**: सभी 12 स्क्रीन्स (`MainMenu`, `LoadingScreen`, `GameplayHUD`, `PauseMenu`, `Settings`, `Shop`, `Inventory`, `Rewards`, `LevelSelection`, `WinLoseScreen`, `Profile`, `DailyRewards`) में `SafeAreaMargin` (`36px/48px`), `>=56px` टच बटन, `create_tween()` बटन बाउंस, `CPUParticles3D` बर्स्ट, कैमरा फीडबैक पल्स और मोबाइल वाइब्रेशन (`vibrate_handheld`) जोड़ता है।
   - **Cycle 3 (4-Bus Audio & Performance)**: `Master`, `Music`, `SFX`, `UI` ऑडियो बस, `AudioStreamGenerator` प्रोसीजरल साउंड, पॉलीफोनी गार्ड (`MIN_SFX_INTERVAL_MS`) और `queue_free()` मेमोरी क्लीनअप को वेरिफाई करता है।
2. **Bottom-Up Independent Reviewer (`scripts/independent_polish_reviewer.py`)**:
   - 0 से शुरू करके 7 श्रेणियों (`Graphics`, `UI/UX`, `Animations`, `Gameplay`, `Audio`, `Mobile Experience`, `Performance`) में असली कोड और सीन के सबूतों के आधार पर स्कोर गिनता है (`100/100` आने पर ही पास करता है)।
3. **Fast 3-Minute Virtual-Screen Movie Maker QA (`scripts/deep_game_verifier_bot.gd` + `scripts/multi_video_inspector.py`)**:
   - अलग सीन `res://scenes/qa_bootstrap.tscn` से (ताकि प्रोडक्शन APK में कभी QA बॉट न जाए) `xvfb-run` + `--write-movie` चलाकर 4 MP4 वीडियो और 4-एंगल कैमरा ग्रिड बनाता है:
     - `ui_shop.mp4`: 3 रेजोल्यूशन (`1080x1920`, `1080x2400`, `2400x1080`), सभी 12 स्क्रीन्स के बटन टैप और Pause/Resume लाइफसाइकिल।
     - `mechanics_lab.mp4`: 4-हिट आर्मर्ड क्रिस्टल ब्लॉक (`HP 4 -> 3 -> 2 -> 1 -> 0 | State=popped`) और 8x8 बोर्ड लाइन-क्लियर सेल्फ-टेस्ट।
     - `multi_levels.mp4` / `endless_chunks.mp4`: **Levels 1, 3, 6, 8, 10, 16, 30** (या 5 स्टिच्ड एंडलेस चंक्स) को खेलकर मेमोरी लीक और `PhysicsRayQueryParameters3D` सीम-गैप चेक करता है।
     - `save_ads_and_edge.mp4`: `user://savegame.json` सेव/लोड राउंड-ट्रिप, ऑफलाइन Ad/IAP रेजिलिएंस और `WinLoseScreen` ट्रांजिशन चेक करता है।

---

## 4. किसी भी AI Agent के लिए नॉन-स्टॉप मल्टी-गेम टेस्ट और डिप्लॉयमेंट प्रॉम्प्ट

```text
AUTONOMOUS NON-STOP MISSION: DEPLOY AI GAME STUDIO V5.0 TO `pocketagent98-ai/gift-hub-raipur`, STRESS-TEST BOTH GAME CREATION MODES (PLAY STORE/APK MODE + USER IDEA MODE), AND BUILD MY FINAL SIGNED APK & AAB

TARGET GITHUB REPOSITORY:
- Repository: `pocketagent98-ai/gift-hub-raipur` (`https://github.com/pocketagent98-ai/gift-hub-raipur`)
- Branch: `main`
- Primary Production Game Target: `GAME_ID: block_juggle_cleanroom_01` based on `https://play.google.com/store/apps/details?id=com.block.juggle` (100% Clean-Room Original IP + Positive & Negative Review Upgrades).

ATTACHED FILES:
1. `ai_game_studio_v5_dual_mode_master.zip` (Complete Godot 4.7.2 Studio V5.0 + Dual-Mode Engine + 24 Specialist Agents + 54/54 passing verification suite).
2. `AI_GAME_STUDIO_COMPLETE_DEEP_DIVE_BIBLE_AND_PROMPT.md` (Complete A-to-Z technical architecture and file reference).

NON-NEGOTIABLE OPERATING RULES:
1. WORK NON-STOP UNTIL 100% GREEN (Whether it takes 2 hours, 4 hours, or 24 hours): Never stop early, never give a half-finished report, and never ask me to fix errors manually.
2. NEVER TOUCH GITHUB SECRETS: Keep Repository Settings and Actions Secrets (`GEMINI_API_KEY`, `NVIDIA_API_KEY`, `HF_TOKEN`, `HF_PRIVATE_DATASET_REPO`, `ANDROID_KEYSTORE_PASSWORD`) completely untouched.
3. PRESERVE EXACT TOOL & MODEL ROUTING:
   - Godot 4.7.2 Stable (`gl_compatibility`), Android Target SDK 36 (`minSdkVersion 24`), Step 0 25+ GB disk cleanup.
   - Coding Agent: DeepSeek Harness (`dsh`) ONLY on private NVIDIA NIM route (`nemotron-3-super-120b-a12b`, `nemotron-3.5-lightning-30b-a3b`, `nemotron-3-ultra-550b-a55b`, `nemotron-4-340b-instruct`, `nemotron-nano-3-30b-a3b`, `kimi-k3.1-pro`) + `gemma-4-31b-it`.
   - Video/Audio QA: `gemini-3.5-flash-lite` (500 RPD) + `gemini-3.1-flash-lite` (500 RPD) first, then `gemini-2.5-flash`, then starred NVIDIA Omni fallback `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.
   - Decision Gate: `gemini-decision-1` (200 RPM, 10,000 RPD).
   - Skills: `awesome-gamedev-agent-skills`, `godogen`, `cloudflare/security-audit-skill`, `replica-skill`, `craft-anything`, and `morluto/rea` (Standby).

EXECUTE THESE EXACT PHASES IN ORDER:

PHASE 1 — CLEAN REPO HISTORY & VERIFY DUAL-MODE (PATH A + PATH B + UPDATE MODE) LOCALLY:
1. Clone `https://github.com/pocketagent98-ai/gift-hub-raipur.git` and delete all existing working-tree files except `.git`:
   `find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +`
2. Extract `ai_game_studio_v5_dual_mode_master.zip` into the repo root.
3. Run `python3 test/run_v2_verification_suite.py` and verify all 54/54 checks pass (this automatically tests Path A: Play Store/APK Reference Mode on `com.block.juggle`, Path B: Pure User Idea Mode on `neon_cyber_runner_idea_01` with 5 endless map chunks, and Update Mode via `game_update_and_monetization_controller.py`).
4. Wipe the old messy git commit history into a single clean commit and force-push to `main`:
   git checkout --orphan clean-studio-v5-main
   git add -A
   git commit -m "AI Game Studio V5.0 Dual-Mode Master — Clean History, Review Upgrades & Fast 3m QA"
   git branch -M main
   git push -f origin main

PHASE 2 — LIVE GITHUB ACTIONS EXECUTION & SELF-HEALING LOOP:
1. Trigger `.github/workflows/ai-game-studio.yml` (`workflow_dispatch`) on `main`.
2. Watch and poll the workflow run until all 12 steps (Steps 0 through 11) complete.
3. If ANY step fails in GitHub Actions:
   - Inspect the exact failure log line.
   - Patch the exact script/workflow file so it never gets stuck on that edge case again.
   - Re-run `python3 test/run_v2_verification_suite.py` locally to confirm 54/54 pass.
   - Commit, push to `main`, and re-trigger `.github/workflows/ai-game-studio.yml` immediately.
   - Repeat until the entire workflow finishes Green (Success).

PHASE 3 — FINAL VERIFICATION CHECKLIST BEFORE REPORTING BACK:
Only report completion after confirming from the green GitHub Actions run that:
1. Both Dual-Mode paths (Path A: Play Store Link/APK and Path B: User Original Idea) and all 24 Specialist Agents passed (`54/54` checks).
2. Positive & Negative Play Store reviews of `com.block.juggle` were analyzed and the 3 unique upgrades (`Smart Mercy & Juggle Vault`, `Crystal Fever Overdrive`, `Streak Booster Forge`) were injected into the build.
3. All 4 QA videos (`ui_shop.mp4`, `mechanics_lab.mp4`, `multi_levels.mp4` across Levels 1, 3, 6, 8, 10, 16, 30, and `save_ads_and_edge.mp4`) were recorded via `xvfb-run` + `--write-movie` and verified by `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` / NVIDIA Omni.
4. `build/android/game_install.apk` and `build/android/game_release.aab` (Target SDK 36) were exported, cryptographically verified, and synced to my private Hugging Face Vault (`GAMES_VAULT/block_juggle_cleanroom_01`).
```