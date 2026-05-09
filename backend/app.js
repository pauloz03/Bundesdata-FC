import "dotenv/config";
import express from "express";
import cors from "cors";
import { verifyToken } from "./auth.js";
import { createAuthRouter } from "./authRoutes.js";

const app = express();

/** Vite defaults differ by machine (localhost vs 127.0.0.1); allow both in dev. */
const defaultDevOrigins = [
  "http://localhost:5173",
  "http://127.0.0.1:5173",
];
const envOrigins =
  process.env.FRONTEND_ORIGIN?.split(",")
    .map((o) => o.trim())
    .filter(Boolean) ?? [];
const allowedOrigins = [...new Set([...defaultDevOrigins, ...envOrigins])];

app.use(
  cors({
    origin(origin, callback) {
      if (!origin) {
        return callback(null, true);
      }
      if (allowedOrigins.includes(origin)) {
        return callback(null, true);
      }
      callback(null, false);
    },
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
    optionsSuccessStatus: 204,
  })
);
app.use(express.json());

app.use("/auth", createAuthRouter());

app.get("/", (req, res) => {
  res.send("API is running ");
});

/** Validates Cognito ID token via JWKS (see auth.js). Called by the SPA after sign-in. */
app.get("/protected", verifyToken, (req, res) => {
  res.json({
    ok: true,
    sub: req.user?.sub,
    email: req.user?.email,
  });
});

/** Default 5050: macOS often uses TCP 5000 for AirPlay, which can return 403 to API traffic. */
const PORT = Number(process.env.PORT) || 5050;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
