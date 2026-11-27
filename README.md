# Autonomous AI Game Studio V7.0 (Godot 4.7.2 + Clean-Room Multi-Agent Pipeline)

मोबाइल से 1-क्लिक में **100% ओरिजिनल Android गेम्स (APK + Play Store AAB)** बनाने वाला पूरी तरह ऑटोमैटिक क्लाउड गेम स्टूडियो।

## आपके 2 गेम्स पहले से क्यू (`config/game_queue.json`) में सेट हैं
1. **`game_1` (`block_blast_studio_01`)** — *Crystal Grid Cascade* (8x8 Block Puzzle, `com.block.juggle` के पब्लिक रिव्यूज़ और जॉनर से प्रेरित 100% ओरिजिनल गेम)
2. **`game_2` (`bolt_master_studio_02`)** — *Hexa Bolt Craft* (Layered Screw & Plate Puzzle, `com.quok.screwJam` के पब्लिक रिव्यूज़ और जॉनर से प्रेरित 100% ओरिजिनल गेम)

## मोबाइल से चलाने के सिर्फ़ 3 कदम
1. **बिल्ड और टेस्ट चलाएं:** GitHub → **Actions** → **AI Game Studio V7.0 (4-Stage Autonomous Pipeline)** → **Run workflow** दबाएं और `game_slot` में `game_1` (या `game_2`) चुनें।
2. **अपने फोन में खेलकर चेक करें:** 4 स्टेजेस (रिसर्च → ओरिजिनल एसेट्स → AI Godot बिल्ड → Xvfb 4-वीडियो QA) अपने आप चलेंगे और **Releases** में `game_preview.apk` + 4 गेमप्ले वीडियो आ जाएंगे।
3. **फाइनल पब्लिश लॉक (Approve):** गेम परफेक्ट लगने पर **Actions** → **Stage 5 — Approve, Encrypt & Sign Final Release** चलाएं। यह Play Store सेफ्टी चेक, AES-256 एन्क्रिप्शन (यदि `SCRIPT_AES256_ENCRYPTION_KEY` सेट हो) और Keystore साइनिंग के साथ फाइनल **Release APK + Play Store AAB + Store-Kit** दे देगा।

## 5-स्टेज आर्किटेक्चर (Hugging Face Vault Relay)
| स्टेज | मुख्य काम | AI प्रोवाइडर |
| :--- | :--- | :--- |
| **Stage 1** | पब्लिक Play Store रिव्यू एनालिसिस (`replica-recon` + `replica-entrepreneur`) → 6 गेम बाइबल्स → HF Vault | `gemini-decision-1` + NVIDIA NIM (`nemotron-3-ultra-550b`) |
| **Stage 2** | 100% ओरिजिनल HD एसेट्स (PNG + Musical WAV) → विज़ुअल QA → HF Vault | NVIDIA NIM + `gemini-3.5-flash-lite` |
| **Stage 3** | Multi-Agent Godot 4.7.2 बिल्डर (`.agents/skills/` ऑटो-राउटर) + 3-साइकिल Godot GUI सेल्फ-हील | सिर्फ़ प्राइवेट **NVIDIA NIM** (Anti-429 paced) |
| **Stage 4** | Xvfb वर्चुअल स्क्रीन + 4 Movie Maker MP4 वीडियो + विज़न QA + Preview APK | `gemini-3.5-flash-lite` → `3.1-flash-lite` → `nemotron-3-nano-omni` |
| **Stage 5** | Human Approval → Content Safety + AES-256 + Signed Release APK & AAB + Store Listing | `nemotron-3.5-content-safety` + `nemotron-3-super-120b` |
