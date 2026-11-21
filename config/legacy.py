from datetime import date

LEGACY_URL_NAMES = frozenset(
    {
        "withdraw_application_legacy",
        "staff_application_status_legacy",
        "staff_registration_status_legacy",
        "staff_registration_certificate_legacy",
    }
)

SUNSET_DATE = date(2027, 2, 19)
SUNSET_HTTP = "Fri, 19 Feb 2027 00:00:00 GMT"
