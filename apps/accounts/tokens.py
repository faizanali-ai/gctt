from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Generates and validates tokens for email verification.

    Unlike PasswordResetTokenGenerator, this does NOT include user.last_login in the
    hash value. This ensures that when a user signs up and is automatically logged in
    (which updates last_login), their email confirmation link sent during registration
    remains completely valid.

    The hash includes user.pk, user.is_active, user.email_verified, user.password,
    timestamp, and user.email so changing email/password or verifying invalidates the token.
    """

    def _make_hash_value(self, user, timestamp):
        return (
            f"{user.pk}{user.is_active}{getattr(user, 'email_verified', False)}"
            f"{user.password}{timestamp}{user.email}"
        )


email_verification_token_generator = EmailVerificationTokenGenerator()
