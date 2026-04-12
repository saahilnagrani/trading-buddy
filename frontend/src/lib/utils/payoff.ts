export interface PayoffLeg {
  strike: number;
  instrumentType: "CE" | "PE" | "FUT";
  transactionType: "BUY" | "SELL";
  quantity: number;
  premium: number;
}

export interface PayoffPoint {
  underlying_price: number;
  pnl: number;
}

export interface PayoffResult {
  points: PayoffPoint[];
  maxProfit: number | null;
  maxLoss: number | null;
  breakevens: number[];
}

export function calculatePayoff(
  legs: PayoffLeg[],
  numPoints: number = 200
): PayoffResult {
  if (legs.length === 0) {
    return { points: [], maxProfit: null, maxLoss: null, breakevens: [] };
  }

  const strikes = legs
    .filter((l) => l.instrumentType !== "FUT")
    .map((l) => l.strike);
  const allStrikes = strikes.length > 0 ? strikes : legs.map((l) => l.strike);

  const center =
    allStrikes.reduce((a, b) => a + b, 0) / allStrikes.length;
  const spread =
    allStrikes.length > 1
      ? Math.max(...allStrikes) - Math.min(...allStrikes)
      : center * 0.1;
  const margin = Math.max(spread * 2, center * 0.1);

  const low = center - margin;
  const high = center + margin;
  const step = (high - low) / numPoints;

  const points: PayoffPoint[] = [];
  let prevPnl: number | null = null;
  const breakevens: number[] = [];

  for (let i = 0; i <= numPoints; i++) {
    const spot = low + i * step;
    let totalPnl = 0;

    for (const leg of legs) {
      const multiplier = leg.transactionType === "BUY" ? 1 : -1;
      let pnl = 0;

      if (leg.instrumentType === "CE") {
        const intrinsic = Math.max(0, spot - leg.strike);
        pnl = (intrinsic - leg.premium) * leg.quantity * multiplier;
      } else if (leg.instrumentType === "PE") {
        const intrinsic = Math.max(0, leg.strike - spot);
        pnl = (intrinsic - leg.premium) * leg.quantity * multiplier;
      } else if (leg.instrumentType === "FUT") {
        pnl = (spot - leg.strike) * leg.quantity * multiplier;
      }

      totalPnl += pnl;
    }

    points.push({
      underlying_price: Math.round(spot * 100) / 100,
      pnl: Math.round(totalPnl * 100) / 100,
    });

    if (prevPnl !== null && prevPnl * totalPnl < 0) {
      const prevSpot = low + (i - 1) * step;
      const ratio = Math.abs(prevPnl) / (Math.abs(prevPnl) + Math.abs(totalPnl));
      breakevens.push(Math.round((prevSpot + ratio * step) * 100) / 100);
    }
    prevPnl = totalPnl;
  }

  const pnls = points.map((p) => p.pnl);
  let maxProfit: number | null = Math.max(...pnls);
  let maxLoss: number | null = Math.min(...pnls);

  if (pnls[pnls.length - 1] === maxProfit && pnls[pnls.length - 1] > pnls[pnls.length - 2]) {
    maxProfit = null;
  }
  if (pnls[0] === maxLoss && pnls[0] < pnls[1]) {
    maxLoss = null;
  }

  return { points, maxProfit, maxLoss, breakevens };
}
