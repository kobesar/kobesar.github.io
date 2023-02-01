var margin = { top: 10, right: 30, bottom: 30, left: 40 },
  width = 1000 - margin.left - margin.right,
  height = 500 - margin.top - margin.bottom;

// append the svg object to the body of the page
var svg = d3.select("#dist")
  .append("svg")
  .attr("width", width + margin.left + margin.right)
  .attr("height", height + margin.top + margin.bottom)
  .append("g")
  .attr("transform",
    "translate(" + margin.left + "," + margin.top + ")");

var avgPrice;


var prod = ['d7200', 'nikkor1024', 'tamron2470']

d3.select("#prod")
  .selectAll('myOptions')
  .data(prod)
  .enter()
  .append('option')
  .text(function (d) { return d; }) // text showed in the menu
  .attr("value", function (d) { return d; }) // corresponding value returned by the button

d3.csv('https://raw.githubusercontent.com/kobesar/ebaytracker/master/data/full_data.csv').then(function (data) {
  data = cleanData(data);

  function updateLegend(newData) {
    svg.html("")

    var x = d3.scaleLinear()
      .domain([0, 1000])
      .range([0, width]);

    svg.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x));

    var histogram = d3.histogram()
      .value(function (d) { return d.price; })   // I need to give the vector of value
      .domain(x.domain())  // then the domain of the graphic
      .thresholds(x.ticks(100)); // then the numbers of bins

    // And apply this function to data to get the bins
    var bins = histogram(newData);

    // Y axis: scale and draw:
    var y = d3.scaleLinear()
      .range([height, 0]);
    y.domain([0, d3.max(bins, function (d) { return d.length; })]);   // d3.hist has to be called before the Y axis obviously
    svg.append("g")
      .call(d3.axisLeft(y));

    var appending = svg.selectAll('rect')
      .data(bins).enter()
      .append("rect")
      .attr("x", 1)
      .attr("transform", function (d) { return "translate(" + x(d.x0) + "," + y(d.length) + ")"; })
      .attr("width", function (d) { return x(d.x1) - x(d.x0) - 1; })
      .attr("height", function (d) { return height - y(d.length); })
      .style("fill", "#69b3a2")

    // remove old elements
    appending.exit().remove();
  }

  updateLegend(data);

  d3.select('#prod')
    .on('change', function () {
      var newData = subsetData(data, d3.select(this).property('value'));
      updateLegend(newData);
    });

})

function cleanData(data) {
  var newDat = []
  for (var row of data) {
    row.price = parseFloat(row.price.replace('$', ''))
    if (row.price != -1 && !isNaN(row.price)) {
      newDat.push(row)
    }
  }

  return newDat;

}

function subsetData(data, filter) {
  var newDat = []
  for (var row of data) {
    if (row.product == filter) {
      newDat.push(row)
    }
  }

  return newDat;
}