/** Normalize email for Cognito username (lowercase, trim). */
export function normalizeEmail(input) {
  const email = String(input ?? "")
    .trim()
    .toLowerCase();
  if (!email) {
    throw new Error("Email is required.");
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error("Please enter a valid email address.");
  }
  return email;
}
