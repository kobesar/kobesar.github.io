let dataset, dataset2, svg, circleLabel
let salarySizeScale, salaryXScale, categoryColorScale
let simulation, nodes, scaleR
let categoryLegend, salaryLegend

const margin = { left: 170, top: 50, bottom: 50, right: 20 }
const width = 1000 - margin.left - margin.right
const height = 950 - margin.top - margin.bottom

d3.csv('https://raw.githubusercontent.com/danter2000/STAT423-Project/main/Data/vizdata/circlestest.csv', function (d) {
  return d
}).then(data => {
  dataset = data
  // console.log(dataset)
  setTimeout(getData, 100)
})

function getData() {
  d3.csv('https://raw.githubusercontent.com/danter2000/STAT423-Project/main/Data/vizdata/hof.csv', function (d, i) {
    return {
      player: d.player,
      war: parseInt(d.war),
      as: d.all_stars,
      type: d.type,
      year: d.yearID
    }
  }).then(data => {
    dataset2 = data
    setTimeout(drawInitial, 100)
  })
}

const x = d3.scaleLinear()
  .domain([1, 10])
  .range([300, 550]);

const y = d3.scaleLinear()
  .domain([1, 20])
  .range([150, 650]);

function drawInitial() {
  let svg = d3.select("#vis")
    .append('svg')
    .attr('width', 800)
    .attr('height', 800)
    .attr('margin-right', 'auto')
    .attr('margin-left', 'auto')
    .attr('opacity', 1)

  svg.append('g')
    .selectAll("dot")
    .data(dataset)
    .enter()
    .append("circle")
    .attr('stroke', 'black')
    .attr('fill', '#4b6f84')
    .attr('opacity', 0)
    .attr("cx", function (d) { return x(d.x); })
    .attr("cy", function (d) { return y(d.y); })
    .attr("r", 10)
    .attr("class", function (d) {
      return d.type + " gen"
    })

  makeBeeswarm(dataset2);

  // svg.append('g')
  //   .selectAll("dot")
  //   .data(dataset2)
  //   .enter()
  //   .append("circle")
  //   .attr("fill", "#4b6f84")
  //   .attr('opacity', 0)
  //   .attr("cx", x(5))
  //   .attr("cy", y(10))
  //   .attr("r", 4)
  //   .attr("class", function (d) { return d.type + " players" })


  svg.selectAll("circle.gen")
    .transition()
    .duration(100)
    .attr('opacity', 1)

  circleLabel = svg.append("g")

  circleLabel.append("text")
    .text("Each circle represents roughly 100 players")
    .attr("x", x(11))
    .attr("y", y(1) - 60)
    .call(wrap, 150)

  circleLabel.append("line")
    .style("stroke", "black")
    .attr("x1", x(10) + 10)
    .attr("y1", y(1) - 15)
    .attr("x2", x(11))
    .attr("y2", y(1) - 40)
}

function draw1() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll("circle.gen")
    .transition()
    .duration(1000)
    .attr("opacity", 1)

  circleLabel
    .transition()
    .duration(1000)
    .attr("opacity", 1)
}

function draw2() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".all")
    .transition("circle")
    .duration(1000)
    .attr("opacity", 0.2)

  circleLabel
    .transition("label")
    .duration(1000)
    .attr("opacity", 0)
}

function draw3() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".eligible")
    .transition()
    .duration(1000)
    .attr("opacity", 0.5)
}

function draw4() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".all")
    .transition()
    .duration(1000)
    .attr("opacity", 0)

  svg.selectAll(".eligible")
    .transition()
    .duration(1000)
    .attr("opacity", 0)
}

function draw5() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".inducted")
    .transition()
    .duration(1000)
    .attr("cx", (d) => {
      return x(d.x);
    })
    .attr("cy", (d) => {
      return y(d.y);
    })
    .attr("r", 10)

  svg.selectAll(".players")
    .transition()
    .duration(1000)
    .attr("opacity", 0)


}

function draw6() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".inducted")
    .transition()
    .duration(1000)
    .attr('opacity', 1)
    .attr("cx", (d) => {
      return x(parseInt(d.x) + 3);
    })
    .attr("cy", (d) => {
      return y(parseInt(d.y) + 9);
    })

  svg.selectAll(".players")
    .transition()
    .duration(1000)
    .attr("cx", x(5))
    .attr("cy", y(10))
    .attr('opacity', 0)
}

function draw7() {
  svg = d3.select("#vis").select("svg")

  svg.selectAll(".inducted")
    .transition()
    .duration(500)
    .attr("cx", (d) => {
      return x(parseInt(5));
    })
    .attr("opacity", 0)
    .end()
    .then((d) => {
      const path = d3.path();
      path.moveTo(x(5), y(0));
      path.lineTo(x(5), y(20)); 
      path.closePath();
      
      svg.append("path")
        .attr("fill", "none")
        .attr("stroke-color", "black")
        .attr("class", "line")
        .style("stroke-dasharray", ("3, 3"))  // <== This line here!!
        .attr("d", path);

      svg.selectAll(".players")
        .transition("specific")
        .duration(2000)
        .delay(function (d, i) {
          return i / 30;
        })
        .attr('opacity', 1)
        .attr('cx', (d) => { return d.x })
        .attr('cy', (d) => { return d.y })
        .attr('r', (d) => { return scaleR(d.war) })
    })
}

let activationFunctions = [
  draw1,
  draw2,
  draw3,
  draw4,
  draw5,
  draw6,
  draw7
]

//All the scrolling function
//Will draw a new graph based on the index provided by the scroll


let scroll = scroller()
  .container(d3.select('#graphic'))
scroll()

let lastIndex, activeIndex = 0

scroll.on('active', function (index) {
  d3.selectAll('.step')
    .transition().duration(500)
    .style('opacity', function (d, i) { return i === index ? 1 : 0.1; });

  activeIndex = index
  let sign = (activeIndex - lastIndex) < 0 ? -1 : 1;
  let scrolledSections = d3.range(lastIndex + sign, activeIndex + sign, sign);
  scrolledSections.forEach(i => {
    console.log(activationFunctions[i])
    activationFunctions[i]();
  })
  lastIndex = activeIndex;

})

scroll.on('progress', function (index, progress) {
  if (index == 2 & progress > 0.7) {

  }
})

function wrap(text, width) {
  text.each(function () {
    var text = d3.select(this),
      words = text.text().split(/\s+/).reverse(),
      word,
      line = [],
      lineNumber = 0,
      lineHeight = 1.1, // ems
      x = text.attr("x"),
      y = text.attr("y"),
      dy = 0, //parseFloat(text.attr("dy")),
      tspan = text.text(null)
        .append("tspan")
        .attr("x", x)
        .attr("y", y)
        .attr("dy", dy + "em");
    while (word = words.pop()) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > width) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan")
          .attr("x", x)
          .attr("y", y)
          .attr("dy", ++lineNumber * lineHeight + dy + "em")
          .text(word);
      }
    }
  });
}

function makeBeeswarm(dataset) {
  var center;

  scaleR = d3.scaleLinear()
    .domain([d3.min(dataset, function (d) { return d.war; }), d3.max(dataset, function (d) { return d.war; })])
    .range([5, 15])

  svg = d3.select("#vis").select("svg")

  for (var type of ["position", "pitcher"]) {
    if (type == "position") {
      center = 1
    } else {
      center = 9
    }

    var data = dataset.filter((d) => { return d.type == type })

    var node = svg.append('g')
      .selectAll("dot")
      .data(data)
      .enter()
      .append("circle")
      .attr("class", (d) => {
        return "players " + d.type
      })
      .attr("fill", function (d) {
        if (type == "position") {
          return "#003f5c"
        } else {
          return "#ffa600"
        }
      })
      .attr("stroke", "black")
      .attr("r", 0)
      .attr("cx", x(5))
      .attr("cy", y(10))
      .attr("id", (d) => {
        return d.player;
      })
    // .style("fill", "#679f51")
    // .style("fill-opacity", 0.8)
    // .attr("stroke", "black")
    // .style("stroke-width", 1)
    // .on("mouseover", mouseover) // What to do when hovered
    // .on("mousemove", mousemove)
    // .on("mouseleave", mouseleave)
    // .call(d3.drag() // call specific function when circle is dragged
    //   .on("start", dragstarted)
    //   .on("drag", dragged)
    //   .on("end", dragended));

    const simulation = d3.forceSimulation()
      .force('forceX', d3.forceX(x(center)).strength(0.9))
      .force('forceY', d3.forceY(y(10)).strength(0.05))
      .force("charge", d3.forceManyBody().distanceMax(3).distanceMin(2).strength(1)) // Nodes are attracted one each other of value is > 0
      .force("collide", d3.forceCollide().strength(1).radius(function (d) { return (scaleR(d.war)) }).iterations(1)) // Force that avoids circle overlapping

    simulation
      .nodes(data)
      .on("tick", function () {
        // node
        //   .attr("cx", (d, i) => {data[i]['cx'] = d.x; return x(5)})
        //   .attr("cy", (d, i) => {data[i]['cy'] = d.y; return y(10)})
        node
          .attr("cx", (d) => { return d.x })
          .attr("cy", (d) => { return d.y })
      });
  }

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(.03).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(.03);
    d.fx = null;
    d.fy = null;
  }
}