import { Router } from "express";
import {
  CognitoIdentityProviderClient,
  ConfirmSignUpCommand,
  InitiateAuthCommand,
  ResendConfirmationCodeCommand,
  SignUpCommand,
} from "@aws-sdk/client-cognito-identity-provider";
import { computeSecretHash } from "./cognitoSecret.js";
import { normalizeEmail } from "./emailUtil.js";

const region = process.env.COGNITO_REGION;
const clientId =
  process.env.COGNITO_APP_CLIENT_ID || process.env.COGNITO_CLIENT_ID;
/** Only set for confidential app clients that require SECRET_HASH */
const clientSecret = process.env.COGNITO_CLIENT_SECRET;

function getCognitoClient() {
  if (!region) {
    throw new Error("COGNITO_REGION is not set");
  }
  return new CognitoIdentityProviderClient({ region });
}

function secretHashFor(username) {
  if (!clientSecret || !clientId) return undefined;
  return computeSecretHash(username, clientId, clientSecret);
}

export function createAuthRouter() {
  const router = Router();

  router.post("/signup", async (req, res) => {
    const { email, password, name } = req.body || {};
    if (!email || !password) {
      return res
        .status(400)
        .json({ message: "Email and password are required." });
    }
    if (!clientId) {
      return res.status(500).json({
        message:
          "Server is missing COGNITO_APP_CLIENT_ID (or COGNITO_CLIENT_ID) in .env.",
      });
    }

    let emailNorm;
    try {
      emailNorm = normalizeEmail(email);
    } catch (e) {
      return res.status(400).json({ message: e.message });
    }

    try {
      const userAttributes = [{ Name: "email", Value: emailNorm }];
      if (name && String(name).trim()) {
        userAttributes.push({ Name: "name", Value: String(name).trim() });
      }

      const sh = secretHashFor(emailNorm);
      await getCognitoClient().send(
        new SignUpCommand({
          ClientId: clientId,
          Username: emailNorm,
          Password: password,
          ...(sh ? { SecretHash: sh } : {}),
          UserAttributes: userAttributes,
        })
      );

      res.json({
        ok: true,
        message: "Check your email for a verification code.",
      });
    } catch (err) {
      console.error(err);
      if (err?.name === "UsernameExistsException") {
        // If the user exists but is unconfirmed, resend the code instead of
        // blocking the flow forever.
        try {
          const sh = secretHashFor(emailNorm);
          await getCognitoClient().send(
            new ResendConfirmationCodeCommand({
              ClientId: clientId,
              Username: emailNorm,
              ...(sh ? { SecretHash: sh } : {}),
            })
          );

          return res.status(200).json({
            ok: true,
            message:
              "An account with this email already exists. We sent a new verification code to your email.",
          });
        } catch (resendErr) {
          console.warn(
            "Failed to resend confirmation after UsernameExistsException:",
            resendErr
          );
        }
      }

      const message = err?.message || "Sign up failed.";
      res.status(400).json({ message });
    }
  });

  router.post("/login", async (req, res) => {
    const { email, password } = req.body || {};
    if (!email || !password) {
      return res
        .status(400)
        .json({ message: "Email and password are required." });
    }
    if (!clientId) {
      return res.status(500).json({
        message:
          "Server is missing COGNITO_APP_CLIENT_ID (or COGNITO_CLIENT_ID) in .env.",
      });
    }

    let emailNorm;
    try {
      emailNorm = normalizeEmail(email);
    } catch (e) {
      return res.status(400).json({ message: e.message });
    }

    try {
      const sh = secretHashFor(emailNorm);
      const authParams = {
        USERNAME: emailNorm,
        PASSWORD: password,
        ...(sh ? { SECRET_HASH: sh } : {}),
      };

      const out = await getCognitoClient().send(
        new InitiateAuthCommand({
          AuthFlow: "USER_PASSWORD_AUTH",
          ClientId: clientId,
          AuthParameters: authParams,
        })
      );

      if (out.ChallengeName) {
        return res.status(401).json({
          message: `Additional sign-in step required: ${out.ChallengeName}. Complete it in Cognito or the console.`,
          challengeName: out.ChallengeName,
        });
      }

      const auth = out.AuthenticationResult;
      if (!auth?.IdToken) {
        return res.status(401).json({ message: "Login failed: no tokens returned." });
      }

      res.json({
        idToken: auth.IdToken,
        accessToken: auth.AccessToken,
        refreshToken: auth.RefreshToken,
      });
    } catch (err) {
      console.error(err);
      let message = err.message || "Login failed.";
      if (err.name === "NotAuthorizedException") {
        if (
          /not confirmed|not been confirmed|User is not confirmed/i.test(
            err.message || ""
          )
        ) {
          message =
            "This account is not verified yet. Enter the code from your email on the sign-up page.";
        } else {
          message = "Incorrect email or password.";
        }
      } else if (err.name === "UserNotConfirmedException") {
        message =
          "Please verify your email with the code we sent before logging in.";
      }
      res.status(401).json({ message });
    }
  });

  router.post("/confirm-signup", async (req, res) => {
    const { email, code } = req.body || {};
    if (!email || !code) {
      return res.status(400).json({
        message: "Email and confirmation code are required.",
      });
    }
    if (!clientId) {
      return res.status(500).json({
        message:
          "Server is missing COGNITO_APP_CLIENT_ID (or COGNITO_CLIENT_ID) in .env.",
      });
    }

    let emailNorm;
    try {
      emailNorm = normalizeEmail(email);
    } catch (e) {
      return res.status(400).json({ message: e.message });
    }

    const codeTrimmed = String(code).trim();
    if (!codeTrimmed) {
      return res.status(400).json({ message: "Confirmation code is required." });
    }

    try {
      const sh = secretHashFor(emailNorm);
      await getCognitoClient().send(
        new ConfirmSignUpCommand({
          ClientId: clientId,
          Username: emailNorm,
          ConfirmationCode: codeTrimmed,
          ...(sh ? { SecretHash: sh } : {}),
        })
      );

      res.json({ ok: true, message: "Email verified. You can log in." });
    } catch (err) {
      console.error(err);
      let message = err.message || "Verification failed.";
      if (err.name === "CodeMismatchException") {
        message = "Invalid verification code. Try again or request a new code.";
      } else if (err.name === "ExpiredCodeException") {
        message = "That code has expired. Request a new code.";
      } else if (err.name === "NotAuthorizedException") {
        message = err.message || "Unable to confirm.";
      }
      res.status(400).json({ message });
    }
  });

  router.post("/resend-confirmation", async (req, res) => {
    const { email } = req.body || {};
    if (!email) {
      return res.status(400).json({ message: "Email is required." });
    }
    if (!clientId) {
      return res.status(500).json({
        message:
          "Server is missing COGNITO_APP_CLIENT_ID (or COGNITO_CLIENT_ID) in .env.",
      });
    }

    let emailNorm;
    try {
      emailNorm = normalizeEmail(email);
    } catch (e) {
      return res.status(400).json({ message: e.message });
    }

    try {
      const sh = secretHashFor(emailNorm);
      await getCognitoClient().send(
        new ResendConfirmationCodeCommand({
          ClientId: clientId,
          Username: emailNorm,
          ...(sh ? { SecretHash: sh } : {}),
        })
      );

      res.json({ ok: true, message: "A new code has been sent to your email." });
    } catch (err) {
      console.error(err);
      const message = err.message || "Could not resend code.";
      res.status(400).json({ message });
    }
  });

  return router;
}
