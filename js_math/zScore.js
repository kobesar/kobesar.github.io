  // Obtained from https://stackoverflow.com/questions/36575743/how-do-i-convert-probability-into-z-score
  function percentile_z(p) {
    if (p < 0.5) return -percentile_z(1 - p);

    if (p > 0.92) {
      if (p == 1) return Infinity;
      let r = Math.sqrt(-Math.log(1 - p));
      return (((2.3212128 * r + 4.8501413) * r - 2.2979648) * r - 2.7871893) /
        ((1.6370678 * r + 3.5438892) * r + 1);
    }
    p -= 0.5;
    let r = p * p;
    return p * (((-25.4410605 * r + 41.3911977) * r - 18.6150006) * r + 2.5066282) /
      ((((3.1308291 * r - 21.0622410) * r + 23.0833674) * r - 8.4735109) * r + 1);
  }