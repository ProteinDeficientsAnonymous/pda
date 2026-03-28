import express from "express";
import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from "@whiskeysockets/baileys";
import { Boom } from "@hapi/boom";
import qrcode from "qrcode-terminal";
import pino from "pino";

const logger = pino({ level: process.env.LOG_LEVEL || "info" });
const BOT_SECRET = process.env.BOT_SECRET || "";
const PORT = parseInt(process.env.PORT || "3001", 10);

let sock = null;
let isConnected = false;

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_info");
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      logger.info("Scan this QR code with your WhatsApp bot phone number:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "close") {
      isConnected = false;
      const statusCode = new Boom(lastDisconnect?.error)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      logger.warn({ statusCode }, "Connection closed");
      if (shouldReconnect) {
        logger.info("Reconnecting...");
        connectToWhatsApp();
      } else {
        logger.error("Logged out — delete auth_info/ and restart to re-scan QR");
      }
    }

    if (connection === "open") {
      isConnected = true;
      logger.info("WhatsApp connection established");
      logGroupJids();
    }
  });
}

async function logGroupJids() {
  try {
    const groups = await sock.groupFetchAllParticipating();
    logger.info("Joined groups (copy the JID you want as WHATSAPP_GROUP_ID):");
    for (const [jid, group] of Object.entries(groups)) {
      logger.info(`  ${jid}  —  ${group.subject}`);
    }
  } catch (err) {
    logger.warn({ err }, "Could not fetch group list");
  }
}

function requireSecret(req, res, next) {
  if (!BOT_SECRET) {
    return next();
  }
  if (req.headers["x-bot-secret"] !== BOT_SECRET) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

const app = express();
app.use(express.json());

app.get("/status", (_req, res) => {
  res.json({ connected: isConnected });
});

app.post("/send", requireSecret, async (req, res) => {
  const { groupId, message } = req.body;

  if (!groupId || !message) {
    return res.status(400).json({ error: "groupId and message are required" });
  }

  if (!isConnected || !sock) {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }

  try {
    await sock.sendMessage(groupId, { text: message });
    logger.info({ groupId }, "Message sent");
    res.json({ ok: true });
  } catch (err) {
    logger.error({ err, groupId }, "Failed to send message");
    res.status(500).json({ error: "Failed to send message" });
  }
});

app.listen(PORT, () => {
  logger.info(`WhatsApp bot HTTP server listening on port ${PORT}`);
});

connectToWhatsApp();
