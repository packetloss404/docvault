# Backlog

## Portfolio audit backlog — 2026-07-17
_Findings from a 2026-07-17 code audit, preserved for later._

### Later / deferred
- **[low/M]** Single benign TODO at esignatures/views.py:398 — optional SMS provider hook for external signer verification code delivery (currently out-of-band)
  - Fix: Optional: integrate Twilio/AWS SNS to send the 6-digit verification_code via SMS when Signer.phone_number is set, before ExternalSignerVerifyView is hit. Endpoint already works with out-of-band code delivery and is throttled (SigningRateThrottle). Not a defect — deliberate documented design. Verified: this is the only TODO/FIXME/stub in the tree (excl migrations).
