# Striker - OAuth Account Status

| Service | Status | Account | Username |
|---------|--------|---------|----------|
| HuggingFace | ❌ BLOCKED by CAPTCHA | novacline602@gmail.com | — |
| Kaggle | ✅ SUCCESS | novacline602@gmail.com | novacline |
| Replicate | ⏭️ SKIPPED - GitHub only | novacline602@gmail.com | — |

Updated: 2026-04-01 15:56 UTC

## Details

### Kaggle ✅
- **Method**: Google OAuth (Sign in with Google)
- **Flow**: Login → Google Account Chooser → Google Consent (Continue) → Kaggle Registration (Next → I Agree) → Logged in
- **Username**: novacline
- **Profile URL**: kaggle.com/novacline
- **Status**: Fully registered and signed in

### HuggingFace ❌
- **Method**: Attempted email/password registration (no Google OAuth available)
- **Issue**: Registration form requires **hCaptcha** which cannot be solved programmatically via CDP
- **Progress**: Email and password entered, profile form filled (username: novacline602, name: Nova Cline), but form submission blocked by CAPTCHA validation
- **Error**: "Invalid input: expected string, received undefined → at captcha"

### Replicate ⏭️
- **Method**: N/A - Only GitHub OAuth available, no Google OAuth option
- **Sign-in page only shows**: "Sign in with GitHub"
