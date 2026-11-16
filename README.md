# 🏛️ Autonomous AI Game Studio V5.0 — Final Production Release (Godot 4.7.2)

यह पैकेज आपके **80-Page Historical Decision Ledger** और सभी 14 इंजीनियरिंग सुधारों को एकीकृत करके **Godot 4.7.2 Stable**, **DeepSeek Harness (`dsh`)**, **24 Specialist Agents**, **3-Path Original Asset Factory**, और **Private Hugging Face Vault** के साथ एक पूर्ण, सत्यापित और कमर्शियल-ग्रेड मोबाइल गेम स्टूडियो प्रदान करता है।

---

## 🛠️ 1. स्थायी, अस्थायी और स्टैंडबाय टूल्स (Historical Tool Status)

| Tool / Skill / Model | Status | भूमिका (Responsibility) |
| :--- | :--- | :--- |
| **DeepSeek Harness (`dsh`)** + `@ebony-vinyl/dsh-our-free-model@2.8.3` | `PERMANENT` | मुख्य और एकमात्र Coding Agent (OpenCode पूर्णतः हटाया जा चुका है; प्राइवेट रिसर्च के लिए शेयर्ड फ्री लेन ब्लॉक रहती है)। |
| **`gamedev-skills/awesome-gamedev-agent-skills`** | `PERMANENT` | अनिवार्य 77+ सीनियर गेम-डेव स्किल्स और 16 Godot 4.7 कोर नियम (`.agents/skills/awesome-gamedev-agent-skills/SKILL.md`)। |
| **`htdt/godogen`** | `PERMANENT` | स्थायी Godot 4 सीन बिल्डर और 4-कैमरा विज़ुअल QA नियम (`.agents/skills/godogen/SKILL.md`)। |
| **`Jakeschincariol/replica-skill`** (`replica-recon`, `replica-entrepreneur`, `replica-brand`) | `TEMPORARY` | केवल Reference Game Research और Trademark Clean-Room जांच के लिए। |
| **`storytold/craft-anything`** | `TEMPORARY` | केवल Reference Visual Layout और स्क्रीन अनुपात अध्ययन के लिए। |
| **`morluto/rea`** (`rea-agents`) | `STANDBY` | सामान्य स्थिति में शांत (`USE_REA: false`); केवल आपके `ORDER.md` में `USE_REA: true` या `/rea` आदेश पर सक्रिय। |
| **`cloudflare/security-audit-skill`** + **`modern-web-guidance`** | `PERMANENT` | 6-फेज सुरक्षा ऑडिट, लाइसेंस जांच, और लेगसी GDScript/Web कोड स्कैनर। |
| **`gemini-decision-1` + `moonshotai/kimi-k3.1-pro` + 9 Starred NVIDIA Nemotron + `Gemma 4`** | `PERMANENT` | `litellm_config.yaml` और `scripts/gemini_decision_gate.py` द्वारा अपने निर्धारित रोल में सक्रिय। |
| **Godot 4.7.2 Stable + GitHub Actions + Private Hugging Face Vault** | `PERMANENT` | Android 16 (`target_sdk=36`, `min_sdk=24`) Signed `.apk` + `.aab` एक्सपोर्ट और AES-256-CBC एन्क्रिप्टेड कीस्टोर (`release.keystore.enc`)। |

---

## 📂 2. मुख्य स्क्रिप्ट्स और आर्किटेक्चर (Core Components)

1. **`ORDER.md` & `scripts/hf_vault_sync.py`**: आपके Private Hugging Face (`MY_COMMANDS_AND_FILES/`) या लोकल `ORDER.md` से `PLAYSTORE_REFERENCE_LINK`, `REFERENCE_APK_PATH`, `AUTHORIZED_REPO_PATH`, `REFERENCE_VIDEOS`, और `USE_REA` को पढ़कर `docs/resolved_job.json` में रूट करता है और `PUBLIC_AD_IDS.txt` को सुरक्षित रूप से प्रोसेस करता है।
2. **`scripts/deep_game_intelligence.py`, `scripts/apk_and_source_archaeologist.py`, `scripts/review_intelligence.py`**: रेफरेंस गेम के स्टोर मेटाडेटा, कानूनी APK स्ट्रक्चर (और `USE_REA: true` पर REA विश्लेषण), तथा 10 श्रेणियों में प्लेयर रिव्यूज़ का विश्लेषण करते हैं (`[VERIFIED]`, `[OBSERVED]`, `[INFERRED]`, `[UNKNOWN]` टैग्स के साथ)।
3. **`scripts/ui_element_and_interaction_mapper.py` (Dynamic Parser)**: यह कोई हार्डकोडेड टेम्पलेट नहीं है—यह सीधे `.tscn` सीन फाइल्स, `scripts/ui_controller.gd` के 12 स्क्रीन्स, `StyleBoxFlat` कलर्स, `SafeAreaMargin`, `>=56px` टच टारगेट्स, और `Pillow`/SVG के ज़रिए असली इमेज/स्क्रीनशॉट डाइमेंशन्स व कलर्स को डायनामिक रूप से पार्स करके `docs/UI_ELEMENT_AND_INTERACTION_MAP.json` बनाता है।
4. **`scripts/generate_intelligence_dossier.py` & `scripts/generate_complete_game_bible.py`**: 16-सेक्शन का `docs/REFERENCE_INTELLIGENCE_DOSSIER.md` (`.json`) और संपूर्ण `docs/COMPLETE_GAME_BIBLE.md` (`.json`) तैयार करते हैं।
5. **`scripts/original_asset_factory.py` & `scripts/procedural_3d_factory.gd`**: एसेट्स के तीनों वैध रास्ते लागू करते हैं:
   - **Path 1 (Licensed Asset Adaptation)**: केवल `CC0-1.0`, `Public-Domain`, `MIT`, `Apache-2.0`, `CC-BY-4.0` लाइसेंस वाले एसेट्स (SHA-256 और एट्रिब्यूशन रिकॉर्ड के साथ)।
   - **Path 2 (Original Asset Creation)**: Godot 4.7.2 प्रोसीजरल 3D मॉडल्स (`PlayerCharacter3D`, `OriginalArcadeVehicle3D`, 4-हिट बबल्स, बम, सिक्के), ओरिजिनल SVG आइकन्स (`assets/icons/*.svg`), और 44.1kHz PCM `.wav` साउंड इफेक्ट्स (`assets/audio/*.wav`)।
   - **Path 3 (Hybrid Pipeline)**: दोनों का वैध संयोजन + `docs/ASSET_LICENSE_MANIFEST.json` (किसी भी अनधिकृत एसेट या हैश-टैम्परिंग को तुरंत ब्लॉक करता है)।
6. **`scripts/orchestrate_24_agents.py`**: सभी 24 एजेंट्स का वास्तविक निष्पादन करता है। हर एजेंट से पहले `git tag -f safe-AGENT_XX` चेकपॉइंट बनाता है और 3 बार असफल होने पर अपने-आप `git reset --hard safe-AGENT_XX` से ऑटो-रोलबैक करता है।
7. **`scenes/qa_bootstrap.tscn` & `scripts/deep_game_verifier_bot.gd`**: प्रोडक्शन `project.godot` को 100% बॉट-मुक्त रखते हुए 4 फुल-लेंथ वीडियो सूट्स (`ui_shop`, `mechanics_lab`, `multi_levels`/`endless_chunks`, और चौथा `save_ads_and_edge`) तथा 4-एंगल कैमरा ग्रिड (`_capture_4_angles_sync`) चलाता है।

---

## 🚀 3. उपयोग और टेस्टिंग कमांड्स

```bash
# 1. संपूर्ण V5.0 वेरिफिकेशन सूट चलाएं (Python, GDScript, Dynamic UI Mapper, 3-Path Assets, 4th QA Suite, 3-Retry Git Rollback)
python3 test/run_v2_verification_suite.py

# 2. सभी 24 एजेंट्स का एंड-टू-एंड पाइपलाइन चलाएं
python3 scripts/orchestrate_24_agents.py
```
