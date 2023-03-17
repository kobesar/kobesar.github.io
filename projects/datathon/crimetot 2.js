const margin = { top: 10, right: 30, bottom: 30, left: 30 };
const width = 600 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

var crimeTotalSvg = d3.select("#crime-tot")
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .attr("class", "svg-style").append('g')
  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var crimePackSvg = d3.select("#crime-pack")
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .attr("class", "svg-style")

var crimeCriclesSvg = d3.select("#crime-circle")
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .attr("class", "svg-style").append('g')
  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var crimeBeforeSvg = d3.select("#crime-before")
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .attr("class", "svg-style").append('g')
  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var crimeHourSvg = d3.select("#crime-hour")
  .append('svg')
  .attr('width', width + margin.left + margin.right)
  .attr('height', height + margin.top + margin.bottom)
  .attr("class", "svg-style").append('g')
  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var neighborPick = "ALASKA JUNCTION";
var yearPick = 2008;

const parseYear = d3.timeParse("%Y");

d3.csv("https://raw.githubusercontent.com/NSC508/Datathon2023/main/data/crimefull.csv").then(function (data) {
  data = data.filter(function (d) { return d.year != "NA" })

  const xAxis = d3.scaleBand()
    .range([0, width])
    .domain(data.map(d => d.year))
    .padding(0.2);
  crimeBeforeSvg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xAxis)
      .tickSizeOuter(0)
      .tickPadding(10))
    .selectAll("text")
    .attr("transform", "translate(-20,10)rotate(-90)")
    .style("text-anchor", "end")
    .selectAll("line")
    .attr("stroke", "lightgrey");

  const yAxis = d3.scaleLinear()
    .domain([0, 80000])
    .range([height, 0]);
  crimeBeforeSvg.append("g")
    .call(d3.axisLeft(yAxis)
      .tickSizeInner(-width)
      .tickSizeOuter(0)
      .tickPadding(10))
    .selectAll("line")
    .attr("stroke", "lightgrey");

  crimeBeforeSvg.selectAll("mybar")
    .data(data)
    .join("rect")
    .attr("x", d => xAxis(d.year))
    .attr("width", xAxis.bandwidth())
    .attr("fill", "#679f51")
    // .attr("stroke", "black")
    // no bar at the beginning thus:
    .attr("height", d => height - yAxis(0)) // always equal to 0
    .attr("y", d => yAxis(0))

  // Animation
  crimeBeforeSvg.selectAll("rect")
    .transition()
    .duration(800)
    .attr("y", d => yAxis(d.n))
    .attr("height", d => height - yAxis(d.n))
    .delay((d, i) => { return i * 100 })

  crimeBeforeSvg.selectAll("rect")
    .on('mouseover', function (d) {
      d3.select(this)
      .attr("stroke", "black")
      .attr("stroke-width", "2")
    })
    .on('mouseout', function (d) {
      d3.select(this)
      .attr("stroke", "none")
    })
})


d3.csv("https://raw.githubusercontent.com/NSC508/Datathon2023/main/data/neighborsum.csv").then(function (data) {
  data = data.filter(function (d) { return d.year <= 2022 });

  const groups = d3.group(data, d => d.MCPP);

  const xScale = d3.scaleLinear()
    // .domain([new Date("2008"), new Date("2023")])
    .domain(d3.extent(data, function (d) { if (d.year >= 2008) { return d.year; } }))
    .range([10, width]);

  const yScale = d3.scaleLinear()
    .domain([0, d3.max(data, function (d) { return +d.n; }) * 1.3])
    .range([height, 0]);

  const xAxis = d3.axisBottom(xScale)
    .ticks(15)
    .tickFormat(d => d)
    .tickSizeInner(-height)
    .tickSizeOuter(0)
    .tickPadding(10);

  const yAxis = d3.axisLeft(yScale)
    .tickSizeInner(-width)
    .tickSizeOuter(0)
    .tickPadding(10);

  crimeTotalSvg.append("g")
    .attr("transform", `translate(0, ${height})`)
    .call(xAxis)
    .selectAll("line")
    .attr("stroke", "lightgrey");

  crimeTotalSvg.append("g")
    .attr("transform", "translate(10,0)")
    .call(yAxis)
    .selectAll("line")
    .attr("stroke", "lightgrey");

  const line = d3.line()
    // .x(d => xScale(parseYear(d.year)))
    .x(d => xScale(d.year))
    .y(d => yScale(d.n));

  crimeTotalSvg.selectAll('text')
    .data(data)
    .enter()
    .append("text")
    .filter(function (d) { return d.year == 2008 })
    .attr("x", function (d) { return xScale(d.year) })
    .attr("y", function (d) { return yScale(d.n) - 30 })
    .attr('font-size', '10px')
    .attr("text-anchor", "start")
    .attr('class', (d, i) => {
      return d.MCPP.substring(0, 3);
    })
    .style("visibility", "hidden")
    .text(function (d) { return d.MCPP });

  crimeTotalSvg.selectAll('circle')
    .data(data)
    .enter()
    .append('circle')
    .attr('cx', (d) => {
      return xScale(d.year)
    })
    .attr('cy', (d) => {
      return yScale(d.n)
    })
    .attr('r', 4)
    .attr('opacity', 0)
    .attr('fill', '#f4f4f4')
    .attr('stroke', 'black')
    .attr('class', (d, i) => {
      return d.MCPP.substring(0, 3);
    })

  crimeTotalSvg.selectAll('path')
    .data(groups)
    .enter()
    .append('path')
    .attr('d', d => line(d[1]))
    .attr('fill', 'none')
    // .attr('stroke', (d, i) => d3.schemeCategory10[i])
    .attr('stroke', '#679f51')
    .attr('stroke-opacity', 0.3)
    .attr('stroke-width', 2)
    .attr('class', (d, i) => {
      return d[0].substring(0, 3);
    })
    .on("mouseover", function (d, i) {
      var curr = d3.select(this)
      d3.select(this).attr('stroke-opacity', 1).attr('stroke-width', 2.5);
      d3.selectAll("circle." + curr.attr("class"))
        .raise()
        .attr('opacity', 1)
      d3.selectAll("text." + curr.attr("class"))
        .style("visibility", "visible")

    })
    .on("mouseout", function (d, i) {
      var curr = d3.select(this)
      d3.select(this).attr('stroke-opacity', 0.3).attr('stroke-width', 2);
      d3.selectAll("circle." + curr.attr("class"))
        .attr('opacity', 0)
      d3.selectAll("text." + curr.attr("class"))
        .style("visibility", "hidden")
    });
})


d3.csv("https://raw.githubusercontent.com/NSC508/Datathon2023/main/data/offensesum.csv").then(function (data) {
  const tooltip = d3.select('body')
    .append("div")
    .style("opacity", 0)
    .attr("class", "tooltip")
    .style("background-color", "white")
    .style("border", "solid")
    .style("position", "absolute")
    .style("border-width", "2px")
    .style("border-radius", "5px")
    .style("padding", "5px")
    .style("width", "auto")

  const mouseover = function (event, d) {
    d3.select(this)
      .style('fill-opacity', 0.5)

    tooltip
      .style("visibility", "visible")
      .style("opacity", 1)
  }
  const mousemove = function (event, d) {
    const x = event.pageX;
    const y = event.pageY;

    tooltip
      .html('<u>' + d['Offense.Parent.Group'] + '</u>' + "<br>" + parseFloat(d.perc).toFixed(4) + "%")
      .style("left", (x + 20) + "px")
      .style("top", (y - 30) + "px")
  }
  var mouseleave = function (event, d) {
    d3.select(this)
      .style('fill-opacity', 0.8)

    tooltip
      .style("visibility", "hidden")
      .style("opacity", 0)
  }
  const size = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.n)])
    .range([2, 5])  // circle will be between 7 and 55 px wide

  var node = crimePackSvg.append("g")
    .selectAll("circle")
    .data(data)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", 0)
    .attr("cx", width / 2)
    .attr("cy", height / 2)
    .style("fill", "#679f51")
    .style("fill-opacity", 0.8)
    .attr("stroke", "black")
    .style("stroke-width", 1)
    .on("mouseover", mouseover) // What to do when hovered
    .on("mousemove", mousemove)
    .on("mouseleave", mouseleave)
    .call(d3.drag() // call specific function when circle is dragged
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));

  const simulation = d3.forceSimulation()
    .force("center", d3.forceCenter().x((width + margin.left + margin.right) / 2).y((height + margin.top + margin.bottom) / 1.6)) // Attraction to the center of the svg area
    .force("charge", d3.forceManyBody().strength(.4)) // Nodes are attracted one each other of value is > 0
    .force("collide", d3.forceCollide().strength(.2).radius(function (d) { return (size(d.n) + 2) }).iterations(1)) // Force that avoids circle overlapping

  simulation
    .nodes(data)
    .on("tick", function (d) {
      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y)
    });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      // If the visual is in the viewport, trigger the transition
      if (entry.isIntersecting) {
        crimePackSvg.selectAll("circle")
          .transition()
          .duration(1000)
          .attr("r", (d) => {
            return size(d.n)
          })
      } else {
        crimePackSvg.selectAll("circle")
          .transition()
          .duration(1000)
          .attr("r", 0)
      }
    });
  });

  // Observe the element
  observer.observe(crimePackSvg.node());

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
});

d3.csv("https://raw.githubusercontent.com/NSC508/Datathon2023/main/data/crimehour.csv").then(function (data) {
  var groups = d3.group(data, d => d['Offense.Parent.Group'])

  const xScale = d3.scaleLinear()
    // .domain([new Date("2008"), new Date("2023")])
    .domain([1, 24])
    .range([10, width]);

  const xAxis = d3.axisBottom(xScale)
    .ticks(15)
    .tickFormat(d => d)
    .tickSizeInner(-height)
    .tickSizeOuter(0)
    .tickPadding(10);

  changeLines("report", false)

  d3.select("#report-input")
    .on("change", (d) => {
      var reportType = d3.select('input[name="report-type"]:checked').property("value");
      var norm = d3.select('input[name="norm"]').property("checked");

      changeLines(reportType, norm);
    })

  function changeLines(reportType, norm) {
    var color = d3.scaleOrdinal(d3.schemeCategory10)
    // .range(['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999', '#'])
    crimeHourSvg.html("")

    var userPick;
    if (reportType == "report" && norm) {
      userPick = 'report_norm'
    } else if (reportType == "report" && !norm) {
      userPick = 'n_reports'
    } else if (norm) {
      userPick = 'start_norm'
    } else {
      userPick = 'n_starts'
    }

    crimeHourSvg.append("g")
      .attr("transform", `translate(0, ${height})`)
      .call(xAxis)
      .selectAll("line")
      .attr("stroke", "lightgrey");

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(data, function (d) { return +d[userPick]; }) * 1.3])
      .range([height, 0]);

    const yAxis = d3.axisLeft(yScale)
      .tickSizeInner(-width)
      .tickSizeOuter(0)
      .tickPadding(10);

    crimeHourSvg.append("g")
      // .attr("transform", "translate(0,0)")
      .call(yAxis)
      .selectAll("line")
      .attr("stroke", "lightgrey");

    const line = d3.line()
      // .x(d => xScale(parseYear(d.year)))
      .x(d => xScale(d.start_hour))
      .y(d => yScale(d[userPick]));

    crimeHourSvg.selectAll('text')
      .data(data)
      .enter()
      .append("text")
      .attr("x", function (d) { if (d.start_hour == '24') { return xScale(d.start_hour) } })
      .attr("y", function (d) { if (d.start_hour == '24') { return yScale(d[userPick]) - 10 } })
      .attr('font-size', '10px')
      .attr("text-anchor", "start")
      .attr('class', (d, i) => {
        return d['Offense.Parent.Group'].substring(0, 3);
      })
      .style("visibility", "hidden")
      .text(function (d) { return d['Offense.Parent.Group'] });

    crimeHourSvg.selectAll('path')
      .data(groups)
      .enter()
      .append('path')
      .attr('d', d => line(d[1]))
      .attr('fill', 'none')
      .attr("stroke", function (d, i) { return color(i) })
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.5)
      .attr('class', function (d, i) { return d[0].substring(0, 3) })
      .on("mouseover", function (d) {
        var curr = d3.select(this)
        d3.select(this).attr('stroke-opacity', 1).attr('stroke-width', 2);
        d3.selectAll("text." + curr.attr("class"))
          .style("visibility", "visible")
      })
      .on("mouseout", function (d) {
        var curr = d3.select(this)
        d3.select(this).attr('stroke-opacity', 0.5).attr('stroke-width', 1);
        d3.selectAll("text." + curr.attr("class"))
          .style("visibility", "hidden")
      });

    // crimeHourSvg.selectAll('circle')
    //   .data(data)
    //   .enter()
    //   .append('circle')
    //   .attr('cx', (d) => {
    //     return xScale(d.start_hour)
    //   })
    //   .attr('cy', (d) => {
    //     return yScale(d[userPick])
    //   })
    //   .attr('r', 2)
    //   .attr('stroke-width', 1)


  }
})