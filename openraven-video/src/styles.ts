export const colors = {
  dark: "#1a1a1a",
  warmCream: "#fef9ef",
  brand: "#fa520f",
  brandFlame: "#fb6424",
  brandAmber: "#ffa110",
  brandGold: "#ffd900",
  text: "#1f1f1f",
  textMuted: "#666666",
  textLight: "#999999",
  white: "#ffffff",
  darkOrange: "#d94800",
  gold: "#b8860b",
};

export const FRAME_RATE = 30;

// Beat timing in frames (at 30fps)
export const beats = {
  hook:  { from: 0,    duration: 420  }, // 0-14s
  turn:  { from: 420,  duration: 120  }, // 14-18s
  upload:{ from: 540,  duration: 180  }, // 18-24s
  graph: { from: 720,  duration: 240  }, // 24-32s
  ask:   { from: 960,  duration: 240  }, // 32-40s
  trust: { from: 1200, duration: 240  }, // 40-48s
  cta:   { from: 1440, duration: 210  }, // 48-55s
};

export const TOTAL_FRAMES = 1650; // 55s at 30fps
