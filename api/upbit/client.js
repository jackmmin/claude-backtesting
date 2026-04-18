const https = require("https");

const UPBIT_BASE = "https://api.upbit.com/v1";

function fetchUpbit(endpoint) {
  return new Promise((resolve, reject) => {
    https
      .get(UPBIT_BASE + endpoint, { headers: { Accept: "application/json" } }, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(JSON.parse(data)));
      })
      .on("error", reject);
  });
}

module.exports = { fetchUpbit };
