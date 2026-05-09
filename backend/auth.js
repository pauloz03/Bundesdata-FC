import jwt from "jsonwebtoken";
import jwksClient from "jwks-rsa";

const region = process.env.COGNITO_REGION;
const userPoolId = process.env.COGNITO_USER_POOL_ID;
const appClientId =
  process.env.COGNITO_APP_CLIENT_ID || process.env.COGNITO_CLIENT_ID;

if (!region || !userPoolId) {
  console.warn(
    "[auth] COGNITO_REGION and COGNITO_USER_POOL_ID must be set for JWT verification."
  );
}

const issuer =
  region && userPoolId
    ? `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`
    : null;

const client =
  region && userPoolId
    ? jwksClient({
        jwksUri: `https://cognito-idp.${region}.amazonaws.com/${userPoolId}/.well-known/jwks.json`,
      })
    : null;

function getKey(header, callback) {
  if (!client) {
    return callback(new Error("JWKS client not configured"));
  }
  client.getSigningKey(header.kid, function (err, key) {
    if (err) {
      return callback(err);
    }
    const signingKey = key.getPublicKey();
    callback(null, signingKey);
  });
}

export function verifyToken(req, res, next) {
  if (!issuer || !client) {
    return res.status(500).json({
      message: "Server auth is not configured (missing Cognito env vars).",
    });
  }

  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ message: "Missing or invalid Authorization header" });
  }

  const token = authHeader.slice(7).trim();
  if (!token) {
    return res.status(401).json({ message: "Missing token" });
  }

  const verifyOptions = {
    algorithms: ["RS256"],
    issuer,
  };
  if (appClientId) {
    verifyOptions.audience = appClientId;
  }

  jwt.verify(token, getKey, verifyOptions, (err, decoded) => {
    if (err) {
      return res.status(401).json({ message: "Invalid token" });
    }

    req.user = decoded;
    next();
  });
}
