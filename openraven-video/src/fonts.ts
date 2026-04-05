import { loadFont as loadDMSans } from "@remotion/google-fonts/DMSans";
import { loadFont as loadNotoSansTC } from "@remotion/google-fonts/NotoSansTC";
import { cancelRender, continueRender, delayRender } from "remotion";

const dmSans = loadDMSans("normal", {
  weights: ["400", "500", "700"],
  subsets: ["latin"],
});

const notoSansTC = loadNotoSansTC("normal", {
  weights: ["400", "500", "700"],
  subsets: ["latin"],
});

export const fontBody = dmSans.fontFamily;
export const fontChinese = notoSansTC.fontFamily;

const delay = delayRender("Loading fonts");

Promise.all([dmSans.waitUntilDone(), notoSansTC.waitUntilDone()])
  .then(() => continueRender(delay))
  .catch((err) => cancelRender(err));
