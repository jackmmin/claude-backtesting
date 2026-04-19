const registry = {
  upbit: require("./upbit"),
};

function getExchange(name = "upbit") {
  const exchange = registry[name];
  if (!exchange) throw new Error(`Unknown exchange: ${name}`);
  return exchange;
}

module.exports = { getExchange };
