// Scrollytelling for the HOF report. 11 sections, 11 draw functions.
// Loads data from ./data/ (copied from STAT423-Project/Data/vizdata/).

let dataset, dataset2, oddsPos, oddsPitch
let svg, circleLabel, forestG, endG
let scaleR

const HOT_TAKES = ["Adrian Beltre", "Yadier Molina", "Joe Torre", "Curt Schilling"]

Promise.all([
  d3.csv('data/circlestest.csv'),
  d3.csv('data/hof.csv', d => ({
    player: d.player,
    war: +d.war,
    as: +d.all_stars,
    type: d.type,
    year: d.yearID
  })),
  d3.csv('data/odds_pos.csv', d => ({ term: d.term, or: +d.odds_ratio, lo: +d.ci_low, hi: +d.ci_high })),
  d3.csv('data/odds_pitch.csv', d => ({ term: d.term, or: +d.odds_ratio, lo: +d.ci_low, hi: +d.ci_high }))
]).then(([a, b, c, d]) => {
  dataset = a; dataset2 = b; oddsPos = c; oddsPitch = d;
  drawInitial();
})

const x = d3.scaleLinear().domain([1, 10]).range([300, 550])
const y = d3.scaleLinear().domain([1, 20]).range([150, 650])

function drawInitial() {
  svg = d3.select("#vis")
    .append('svg')
    .attr('width', 1000)
    .attr('height', 900)

  svg.append('g').attr('class', 'grid')
    .selectAll("circle")
    .data(dataset)
    .enter()
    .append("circle")
    .attr('stroke', 'black')
    .attr('fill', '#4b6f84')
    .attr('opacity', 1)
    .attr("cx", d => x(d.x))
    .attr("cy", d => y(d.y))
    .attr("r", 10)
    .attr("class", d => d.type + " gen")

  makeBeeswarm(dataset2)

  circleLabel = svg.append("g").attr("class", "circle-label").attr("opacity", 1)
  circleLabel.append("text")
    .text("Each circle represents roughly 100 players")
    .attr("x", x(11))
    .attr("y", y(1) - 60)
    .call(wrap, 150)
  circleLabel.append("line")
    .style("stroke", "black")
    .attr("x1", x(10) + 10).attr("y1", y(1) - 15)
    .attr("x2", x(11)).attr("y2", y(1) - 40)

  forestG = svg.append("g").attr("class", "forest").attr("opacity", 0).style("pointer-events", "none")
  endG = svg.append("g").attr("class", "end").attr("opacity", 0).style("pointer-events", "none")
}

// Full state setter -- every draw calls this so nothing can get stuck.
function setStage({
  gridAll = 0,      // opacity of .all grid circles
  gridEligible = 0, // opacity of .eligible
  gridInducted = 0, // opacity of .inducted
  label = 0,        // circleLabel opacity
  beeswarm = 0,     // beeswarm opacity
  bwFill = null,    // custom fill fn(d) or null = default
  bwOpacity = null, // custom opacity fn(d) or null = beeswarm flat
  forest = 0,       // forestG opacity
  end = 0,          // endG opacity
  duration = 800
}) {
  clearAnnotations()
  const gridOp = { all: gridAll, eligible: gridEligible, inducted: gridInducted }
  svg.selectAll(".gen")
    .interrupt("gridOp")
    .transition("gridOp").duration(duration)
    .attr("opacity", function () {
      const c = this.getAttribute("class") || ""
      if (c.includes("all")) return gridOp.all
      if (c.includes("eligible")) return gridOp.eligible
      if (c.includes("inducted")) return gridOp.inducted
      return 0
    })
  svg.selectAll(".gen").transition("gridFill").duration(duration).attr("fill", "#4b6f84")
  circleLabel.interrupt("lbl").transition("lbl").duration(duration).attr("opacity", label)

  svg.selectAll(".players")
    .interrupt("bwOp")
    .transition("bwOp").duration(duration)
    .attr("opacity", bwOpacity ? bwOpacity : beeswarm)
  svg.selectAll(".players")
    .transition("bwFill").duration(duration)
    .attr("fill", bwFill ? bwFill : d => d.type === "position" ? "#003f5c" : "#ffa600")
  svg.selectAll(".players")
    .transition("bwR").duration(duration)
    .attr("r", d => scaleR(d.war))

  forestG.interrupt("fOp").transition("fOp").duration(duration).attr("opacity", forest)
  endG.interrupt("eOp").transition("eOp").duration(duration).attr("opacity", end)
}

function clearAnnotations() {
  svg.selectAll(".annotation").remove()
}

// ---------- draw functions (one per section) ----------

// 0: intro -- grid fully visible
function draw1() {
  setStage({ gridAll: 1, gridEligible: 1, gridInducted: 1, label: 1 })
}

// 1: 5000 eligible -- dim ineligible
function draw2() {
  setStage({ gridAll: 0.15, gridEligible: 1, gridInducted: 1 })
}

// 2: 330 inducted / 1%
function draw3() {
  setStage({ gridAll: 0.15, gridEligible: 0.5, gridInducted: 1 })
}

// 3: transition -- hide grid, reveal beeswarm
function draw4() {
  setStage({ beeswarm: 1, duration: 1000 })
}

// 4: beeswarm observations
function draw5() {
  setStage({ beeswarm: 1 })
  setTimeout(() => {
    if (d3.select(".forest").attr("opacity") > 0) return
    const g = svg.append("g").attr("class", "annotation").attr("opacity", 0)
    g.append("text").text("Position players").attr("x", x(1)).attr("y", y(19)).attr("text-anchor", "middle").style("font-weight", "bold").style("font-style", "normal")
    g.append("text").text("Pitchers").attr("x", x(9)).attr("y", y(19)).attr("text-anchor", "middle").style("font-weight", "bold").style("font-style", "normal")
    g.append("text").text("larger = higher career WAR").attr("x", x(5)).attr("y", y(20) + 20).attr("text-anchor", "middle").attr("fill", "#666")
    g.transition().duration(600).attr("opacity", 1)
  }, 400)
}

// 5: All-Star highlight
function draw6() {
  const asMax = d3.max(dataset2, d => d.as) || 20
  const asColor = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, asMax])
  setStage({ beeswarm: 1, bwFill: d => asColor(d.as || 0) })
  setTimeout(() => {
    const g = svg.append("g").attr("class", "annotation").attr("opacity", 0)
    g.append("text").text("Brighter = more All-Star selections").attr("x", x(5)).attr("y", y(0) + 20).attr("text-anchor", "middle").attr("fill", "#666")
    g.append("text").text("Each selection: 3.3x (pitchers) / 3.75x (position) odds of induction").attr("x", x(5)).attr("y", y(0) + 40).attr("text-anchor", "middle").attr("fill", "#444").style("font-weight", "bold").style("font-style", "normal")
    g.transition().duration(600).attr("opacity", 1)
  }, 400)
}

// 6: Pitcher wins highlight
function draw7() {
  setStage({
    bwOpacity: d => d.type === "pitcher" ? 1 : 0.08,
    bwFill: d => d.type === "pitcher" ? "#ffa600" : "#003f5c"
  })
  setTimeout(() => {
    const g = svg.append("g").attr("class", "annotation").attr("opacity", 0)
    g.append("text").text("Pitchers only").attr("x", x(9)).attr("y", y(19)).attr("text-anchor", "middle").style("font-weight", "bold").style("font-style", "normal")
    g.append("text").text("+18% odds per career Win (OR 1.183, CI [1.08, 1.39])").attr("x", x(5)).attr("y", y(0) + 40).attr("text-anchor", "middle").attr("fill", "#444").style("font-weight", "bold").style("font-style", "normal")
    g.transition().duration(600).attr("opacity", 1)
  }, 400)
}

// 7: Forest plot -- position players
function draw8() {
  setStage({ forest: 1 })
  drawForest(oddsPos, "Position Player Model")
}

// 8: Forest plot -- pitchers
function draw9() {
  setStage({ forest: 1 })
  drawForest(oddsPitch, "Pitcher Model")
}

// 9: Hot takes -- beeswarm with flagged players
function draw10() {
  setStage({
    bwOpacity: d => HOT_TAKES.includes(d.player) ? 1 : 0.12,
    bwFill: d => HOT_TAKES.includes(d.player) ? "#c0392b" : (d.type === "position" ? "#003f5c" : "#ffa600")
  })
  setTimeout(() => {
    const g = svg.append("g").attr("class", "annotation").attr("opacity", 0)
    dataset2.filter(d => HOT_TAKES.includes(d.player)).forEach(d => {
      g.append("text")
        .text(d.player)
        .attr("x", (d.x || x(5)) + 14)
        .attr("y", (d.y || y(10)) + 4)
        .attr("fill", "#c0392b")
        .style("font-weight", "bold")
        .style("font-style", "normal")
    })
    g.append("text").text("Players the model and the voters disagree on").attr("x", x(5)).attr("y", y(0) + 40).attr("text-anchor", "middle").attr("fill", "#444").style("font-weight", "bold").style("font-style", "normal")
    g.transition().duration(600).attr("opacity", 1)
  }, 400)
}

// 10: End
function draw11() {
  setStage({ end: 1, duration: 600 })
  endG.selectAll("*").remove()
  const lines = [
    { t: "About 1 in 100 players make it.", y: 8, size: 28, bold: true, color: "#222" },
    { t: "All-Stars, Wins, and the Veterans Committee explain most of who gets in.", y: 10, size: 16, bold: false, color: "#444" },
    { t: "Narrative, character, and reputation explain the rest.", y: 11.5, size: 16, bold: false, color: "#777" }
  ]
  lines.forEach((l, i) => {
    endG.append("text")
      .text(l.t)
      .attr("x", x(5)).attr("y", y(l.y))
      .attr("text-anchor", "middle")
      .style("font-size", l.size + "px")
      .style("font-style", "normal")
      .style("font-weight", l.bold ? "bold" : "normal")
      .attr("fill", l.color)
      .attr("opacity", 0)
      .attr("transform", `translate(0, 20)`)
      .transition()
      .delay(300 + i * 400)
      .duration(800)
      .attr("opacity", 1)
      .attr("transform", "translate(0, 0)")
  })
}

// ---------- forest plot (animated) ----------
function drawForest(data, title) {
  forestG.selectAll("*").remove()

  const left = 280, right = 820, top = 200, rowH = 75
  const displayMin = 0.5, displayMax = 20
  const xF = d3.scaleLog().domain([displayMin, displayMax]).range([left, right]).clamp(true)

  forestG.append("text")
    .text(title + " — odds ratios (95% CI, log scale)")
    .attr("x", (left + right) / 2).attr("y", top - 60)
    .attr("text-anchor", "middle")
    .style("font-size", "18px").style("font-weight", "bold").style("font-style", "normal")
    .attr("opacity", 0)
    .transition().duration(500).attr("opacity", 1)

  // reference line at OR=1 (animated grow)
  const refLine = forestG.append("line")
    .attr("x1", xF(1)).attr("x2", xF(1))
    .attr("y1", top - 20).attr("y2", top - 20)
    .attr("stroke", "#999").attr("stroke-dasharray", "3,3")
  refLine.transition().duration(700).attr("y2", top + rowH * data.length + 10)

  forestG.append("text").text("no effect (OR = 1)")
    .attr("x", xF(1)).attr("y", top - 25)
    .attr("text-anchor", "middle").attr("fill", "#999").style("font-size", "11px")
    .attr("opacity", 0)
    .transition().delay(400).duration(400).attr("opacity", 1)

  const axis = d3.axisBottom(xF).tickValues([0.5, 1, 2, 5, 10, 20]).tickFormat(d => d + "x")
  const axisG = forestG.append("g")
    .attr("transform", `translate(0, ${top + rowH * data.length + 20})`)
    .attr("opacity", 0)
    .call(axis)
  axisG.transition().delay(600).duration(500).attr("opacity", 1)

  const fmt = v => v > 1000 ? d3.format(".2s")(v) : d3.format(".2f")(v)

  data.forEach((row, i) => {
    const yy = top + i * rowH
    const loD = Math.max(row.lo, displayMin)
    const hiD = Math.min(row.hi, displayMax)
    const orD = Math.min(Math.max(row.or, displayMin), displayMax)
    const delay = 400 + i * 300
    const extreme = row.or > displayMax || row.hi > displayMax

    // label -- fade in from left
    forestG.append("text")
      .text(row.term)
      .attr("x", left - 15).attr("y", yy + 5)
      .attr("text-anchor", "end")
      .style("font-style", "normal").style("font-size", "13px")
      .attr("opacity", 0)
      .transition().delay(delay).duration(400)
      .attr("opacity", 1)

    // CI bar -- grow from OR=1 outward
    const bar = forestG.append("line")
      .attr("x1", xF(1)).attr("x2", xF(1))
      .attr("y1", yy).attr("y2", yy)
      .attr("stroke", "#003f5c").attr("stroke-width", 2)
    bar.transition().delay(delay + 150).duration(700)
      .attr("x1", xF(loD)).attr("x2", xF(hiD))

    // caps
    const capL = forestG.append("line")
      .attr("x1", xF(1)).attr("x2", xF(1))
      .attr("y1", yy).attr("y2", yy)
      .attr("stroke", "#003f5c").attr("stroke-width", 2)
    capL.transition().delay(delay + 600).duration(300)
      .attr("x1", xF(loD)).attr("x2", xF(loD))
      .attr("y1", yy - 6).attr("y2", yy + 6)

    const capR = forestG.append("line")
      .attr("x1", xF(1)).attr("x2", xF(1))
      .attr("y1", yy).attr("y2", yy)
      .attr("stroke", "#003f5c").attr("stroke-width", 2)
    capR.transition().delay(delay + 600).duration(300)
      .attr("x1", xF(hiD)).attr("x2", xF(hiD))
      .attr("y1", yy - 6).attr("y2", yy + 6)

    // point -- pop in
    forestG.append("circle")
      .attr("cx", xF(orD)).attr("cy", yy).attr("r", 0)
      .attr("fill", "#c0392b")
      .transition().delay(delay + 500).duration(400)
      .attr("r", 6)

    // value text -- fade
    forestG.append("text")
      .text(`OR ${fmt(row.or)} [${fmt(row.lo)}, ${fmt(row.hi)}]${extreme ? "  (extends off-chart)" : ""}`)
      .attr("x", right + 20).attr("y", yy + 5)
      .style("font-style", "normal").style("font-size", "11px")
      .attr("fill", extreme ? "#c0392b" : "#333")
      .attr("opacity", 0)
      .transition().delay(delay + 800).duration(400)
      .attr("opacity", 1)
  })
}

// ---------- activation map ----------
const activationFunctions = [draw1, draw2, draw3, draw4, draw5, draw6, draw7, draw8, draw9, draw10, draw11]

let scroll = scroller().container(d3.select('#graphic'))
scroll()
let lastIndex = 0, activeIndex = 0

scroll.on('active', function (index) {
  d3.selectAll('.step')
    .transition().duration(500)
    .style('opacity', (d, i) => i === index ? 1 : 0.1)
  activeIndex = index
  // Always run the target's draw fn directly so you never land in a stuck state
  // from a skipped intermediate step.
  if (activationFunctions[activeIndex]) activationFunctions[activeIndex]()
  lastIndex = activeIndex
})

scroll.on('progress', function () {})

// ---------- util ----------
function wrap(text, w) {
  text.each(function () {
    const t = d3.select(this)
    const words = t.text().split(/\s+/).reverse()
    let word, line = [], lineNumber = 0
    const lineHeight = 1.1
    const xa = t.attr("x"), ya = t.attr("y")
    let tspan = t.text(null).append("tspan").attr("x", xa).attr("y", ya).attr("dy", "0em")
    while (word = words.pop()) {
      line.push(word)
      tspan.text(line.join(" "))
      if (tspan.node().getComputedTextLength() > w) {
        line.pop(); tspan.text(line.join(" "))
        line = [word]
        tspan = t.append("tspan").attr("x", xa).attr("y", ya).attr("dy", (++lineNumber * lineHeight) + "em").text(word)
      }
    }
  })
}

function makeBeeswarm(data) {
  scaleR = d3.scaleLinear()
    .domain([d3.min(data, d => d.war), d3.max(data, d => d.war)])
    .range([4, 14])

  for (const type of ["position", "pitcher"]) {
    const center = type === "position" ? 1 : 9
    const subset = data.filter(d => d.type === type)

    const node = svg.append('g').attr('class', 'beeswarm-' + type)
      .selectAll("circle")
      .data(subset)
      .enter()
      .append("circle")
      .attr("class", d => "players " + d.type)
      .attr("fill", type === "position" ? "#003f5c" : "#ffa600")
      .attr("stroke", "black")
      .attr("stroke-width", 0.5)
      .attr("r", d => scaleR(d.war))
      .attr("cx", x(center))
      .attr("cy", y(10))
      .attr("opacity", 0)
      .attr("id", d => d.player)
      .on("mouseover", (event, d) => {
        d3.select("#tooltip").style("display", "block")
          .html(`<strong>${d.player}</strong><br>WAR: ${d.war} &nbsp; All-Stars: ${d.as}<br>${d.type}`)
      })
      .on("mousemove", event => {
        d3.select("#tooltip")
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px")
      })
      .on("mouseleave", () => d3.select("#tooltip").style("display", "none"))

    const simulation = d3.forceSimulation()
      .force('forceX', d3.forceX(x(center)).strength(0.9))
      .force('forceY', d3.forceY(y(10)).strength(0.05))
      .force("charge", d3.forceManyBody().distanceMax(3).distanceMin(2).strength(1))
      .force("collide", d3.forceCollide().strength(1).radius(d => scaleR(d.war)).iterations(1))

    simulation.nodes(subset).on("tick", () => {
      node.attr("cx", d => d.x).attr("cy", d => d.y)
    })
  }
}
