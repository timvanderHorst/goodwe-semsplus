# GoodWe SEMS+ Home Assistant Integration

Custom Home Assistant integration for GoodWe SEMS+ using pure requests (no Selenium/browser required).

## Install via HACS (Community Store)

This integration is installed through HACS as a custom repository.

### Prerequisites

- Home Assistant is running
- HACS is installed and configured

### Steps

1. In Home Assistant, open HACS.
2. Click the three-dot menu in the top-right and select `Custom repositories`.
3. Add this repository URL:
   - `https://github.com/timvanderHorst/goodwe-semsplus`
4. Set category to `Integration`.
5. Click `Add`.
6. Search in HACS for `GoodWe SEMS+`.
7. Open the integration and click `Download`.
8. Restart Home Assistant.
9. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
10. Search for `GoodWe SEMS+` and add it.
11. Enter your SEMS+ account email and password.

### Version requirement for HACS

- HACS expects a valid version in `custom_components/goodwe_semsplus/manifest.json`.
- Create a GitHub release tag that matches the manifest version (for example `v0.2.0` for version `0.2.0`).
- If HACS shows "The version can not be used with HACS", verify the manifest version format and that a matching release tag exists.

## Manual installation (alternative)

1. Copy `custom_components/goodwe_semsplus` into your Home Assistant `config/custom_components` folder.
2. Restart Home Assistant.
3. Add the integration from `Settings` -> `Devices & Services`.

## Notes

- Credentials are stored through the Home Assistant config entry flow.
- The integration uses cloud polling.
- If login fails, verify your SEMS+ credentials and that the account can log in at `https://semsplus.goodwe.com`.

## Support

- Issues: `https://github.com/timvanderHorst/goodwe-semsplus/issues`
