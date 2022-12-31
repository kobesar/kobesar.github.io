var margin = { top: 50, right: 50, bottom: 50, left: 50 },
    width = 960 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom,
    padding = 2

var canvas = d3.select("#scatter")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height)

var tooltip = d3.select("#scatter")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

var gen = canvas.append("svg")
var cor = canvas.append("svg")

var label = canvas.append("text")
    .attr("id", "point-label")
    .style('font-size', '10px')
    .style('weight', '100')

var courseLab = canvas.append("text")
    .text("Course: , Score: ")
    .attr("id", "course-label")
    .attr('transform', 'translate(' + (margin.left + width / 2) + ',' + (margin.top) + ")")
    .style('text-anchor', 'middle')
    .style('font-size', '10px')
    .style('weight', '100')

var title = canvas.append("text")
    .text("Course Outcome Index")
    .style('text-anchor', 'middle')
    .style('font-size', '18px')
    .attr("transform", "translate(" + (margin.left + width / 2) + ", 30)")

var x = d3.scaleLinear()
    .domain([-5, 5])
    .range([margin.left, width + margin.right]);

var INNER_HEIGHT = height - margin.top - margin.bottom

var coursePicked = "CSE 143"

const RADIUS = 5
const SEED = 0.5

var specClicked = true;
var corClicked = true;
var depClicked = true;

var ALL_SCORES = [];
var COURSES = new Set();

d3.csv('test2.csv').then(function (d) {
    // make subset of data, containing the course selected
    var generalData = dataFilter(d, "general");
    var courseData = dataFilter(d, "course");

    makeBeeswarm(generalData, {
        color: "#4b2e83",
        radius: RADIUS,
        opacity: 0.1,
        svg: gen,
        class: "gen"
    });

    makeBeeswarm(courseData, {
        color: "#4b2e83",
        radius: RADIUS,
        opacity: 1,
        svg: cor,
        class: "cor"
    });


    makeLabels();

    setTimeout(function () {
        canvas.selectAll(".cor")
            .transition()
            .duration(1000)
            .each(function (d) {
                if (d.course == coursePicked) {
                    makeScoreCard(d);
                    canvas.select("#course-label")
                        .transition()
                        .duration(2000)
                        .text("Course: " + coursePicked + ", Score: " + (Math.round(d.score * 100) / 100))
                        .attr('text-anchor', 'middle')

                    d3.select(this)
                        .attr("id", "selectedCourse")
                        .classed("cor", false)
                        .moveToFront()
                        .transition()
                        .duration(2000)
                        .style('fill', '#b7a57a')
                        .style('opacity', 1)
                        .style('stroke', 'black')
                        .attr('r', RADIUS * 1.5)

                    canvas.append('g')
                        .append('path')
                        .attr('d', [[d.x, d.y], [d.x - 50, d.y - 100]])
                } else {
                    d3.select(this)
                        .on('mouseover', function () {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .style("opacity", 0.8)
                                .attr("r", RADIUS)

                            tooltip.transition()
                                .duration(200)
                                .style("opacity", 1)

                            tooltip.html(d.course + "<br>" + Math.round(d.score * 100) / 100)
                                .style("left", (d.x + 10) + "px")
                                .style("top", (d.y - 15) + "px");
                        })
                        .on("mouseout", function () {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .style("opacity", 0.8)
                                .attr("r", RADIUS * 0.8)

                            tooltip.transition()
                                .duration(500)
                                .style("opacity", 0);
                        })
                        .transition()
                        .duration(3000)
                        .style('fill', '#4b2e83')
                        .style('opacity', 0.8)
                        .attr('r', RADIUS * 0.8)
                }
            })

        makeLegend();




    }, 100)

    function makeBeeswarm(data, options) {
        var xAxis = d3.axisBottom(x);

        canvas.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + (margin.top * 5.5) + ")")
            .call(xAxis);

        var nodes = data.map(function (node, index) {
            return {
                opacity: options.opacity,
                x: x(node.score),
                y: height / 5 + Math.abs(Math.random()),
                score: node.score,
                course: node.course_id
            };
        });

        // Force the points to separate
        var force = d3.forceSimulation(nodes)
            // .force('charge', d3.forceManyBody().strength(1))
            // .force('center', d3.forceCenter(margin.left + width / 2, height / 2 - margin.top*2))
            .force('forceX', d3.forceX((d) => d.x).strength(1))
            .force('forceY', d3.forceY(height * 1 / 2).strength(0.02))
            .force('charge', d3.forceManyBody().strength(1))
            .force('collide', d3.forceCollide().radius(RADIUS).strength(1))
            .on("tick", tick)
            .stop();

        function tick() {
            for (i = 0; i < nodes.length; i++) {
                var node = nodes[i];
                node.cx = node.x;
                node.cy = node.y;
            }
        }

        const NUM_ITERATIONS = 100;
        force.tick(NUM_ITERATIONS);
        force.stop();

        options.svg.selectAll("circle")
            .data(nodes)
            .enter().append("circle")
            .style("fill", options.color)
            .style('stroke', 'black')
            .style('stroke-width', "1")
            .style('opacity', options.opacity)
            .attr('class', options.class)
            .attr("cx", function (d) { return d.x })
            .attr("cy", function (d) { return d.y })
            .attr("r", function (d) {
                if (d.course == coursePicked) {
                    return options.radius * 1.5
                } else {
                    return options.radius
                }
            })

    }

    function makeLabels() {
        var labelPosY = 100;

        canvas.append("svg:defs").append("svg:marker")
            .attr("id", "triangle")
            .attr("refX", 6)
            .attr("refY", 6)
            .attr("markerWidth", 30)
            .attr("markerHeight", 30)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M 0 0 12 6 0 12 3 6")
            .style("fill", "black");

        canvas.append("line")
            .attr("x1", 720)
            .attr("y1", labelPosY + 15)
            .attr("x2", 760)
            .attr("y2", labelPosY + 15)
            .attr("stroke-width", 1)
            .attr("stroke", "black")
            .attr("marker-end", "url(#triangle)");

        canvas.append("svg:defs").append("svg:marker")
            .attr("id", "triangle")
            .attr("refX", 6)
            .attr("refY", 6)
            .attr("markerWidth", 30)
            .attr("markerHeight", 30)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M 0 0 12 6 0 12 3 6")
            .style("fill", "black");

        canvas.append("line")
            .attr("x1", 240)
            .attr("y1", labelPosY + 15)
            .attr("x2", 200)
            .attr("y2", labelPosY + 15)
            .attr("stroke-width", 1)
            .attr("stroke", "black")
            .attr("marker-end", "url(#triangle)");

        canvas.append('text')
            .style('font-size', '10px')
            .attr('transform', 'translate(' + (margin.right + (width / 2) + 250) + ',' + labelPosY + ")")
            .attr('text-anchor', 'middle')
            .text('More completions than expected');


        canvas.append('text')
            .style('font-size', '10px')
            .attr('transform', 'translate(' + (margin.left + (width / 2) - 250) + ',' + labelPosY + ")")
            .attr('text-anchor', 'middle')
            .text('Fewer completions than expected')
    }

    function makeLegend() {
        // Selected course
        canvas.append("circle")
            .attr("cx", 30)
            .attr("cy", 20)
            .attr('r', RADIUS)
            .style("fill", "#b7a57a")
            .style('opacity', 1)
            .style('stroke', 'black')
            .on('mouseover', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .attr("r", RADIUS * 1.5)
            })
            .on('click', function () {
                if (specClicked) {
                    specClicked = false;
                } else {
                    specClicked = true;
                }

                d3.selectAll("#selectedCourse")
                    .style("visibility", function () {
                        if (specClicked) {
                            return "visible";
                        } else {
                            return "hidden";
                        }
                    })
            })
            .on('mouseout', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .attr("r", RADIUS)
            })

        //Specific department courses
        canvas.append("circle")
            .attr("cx", 30)
            .attr("cy", 40)
            .attr('r', RADIUS)
            .style('fill', '#4b2e83')
            .style("stroke", "black")
            .style("stroke-opacity", 0)
            .style('opacity', 0.5)
            .on('mouseover', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .style("stroke-opacity", 1)
                    .attr("r", RADIUS * 1.5)
            })
            .on('click', function () {
                if (corClicked) {
                    corClicked = false;
                } else {
                    corClicked = true;
                }

                d3.selectAll(".cor")
                    .style("visibility", function () {
                        if (corClicked) {
                            return "visible";
                        } else {
                            return "hidden";
                        }
                    })

            })
            .on('mouseout', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .style("stroke-opacity", 0)
                    .attr("r", RADIUS * 0.8)
            })

        // All department courses
        canvas.append("circle")
            .attr("cx", 30)
            .attr("cy", 60)
            .attr('r', RADIUS)
            .style('fill', '#4b2e83')
            .style('stroke', 'black')
            .style("stroke-opacity", 0)
            .style('opacity', 0.1)
            .on('mouseover', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .style("stroke-opacity", 1)
                    .attr("r", RADIUS * 1.5)
            })
            .on('click', function () {
                if (depClicked) {
                    depClicked = false;
                } else {
                    depClicked = true;
                }

                d3.selectAll(".gen")
                    .style("visibility", function () {
                        if (depClicked) {
                            return "visible";
                        } else {
                            return "hidden";
                        }
                    })
            })
            .on('mouseout', function () {
                d3.select(this)
                    .transition()
                    .duration(300)
                    .style("stroke-opacity", 0)
                    .attr("r", RADIUS)
            })

        canvas.append("text")
            .attr("x", 40)
            .attr("y", 20)
            .text(coursePicked)
            .style("font-size", "12px")
            .attr("alignment-baseline", "middle")

        canvas.append("text")
            .attr("x", 40)
            .attr("y", 40)
            .text(coursePicked.match(/\D+/)[0].trim() + " Courses")
            .style("font-size", "12px")
            .attr("alignment-baseline", "middle")

        canvas.append("text")
            .attr("x", 40)
            .attr("y", 60)
            .text("Deparment Averages")
            .style("font-size", "12px")
            .attr("alignment-baseline", "middle")
    }

    function makeScoreCard(d) {
        var percentile = getPercentile(d.score)
        console.log(getScore(75))

        var summaryCard = canvas.append('svg')
            .attr('width', width / 2)
            .attr('height', height / 2);

        var x = d3.scaleLinear().domain([0, 100]).range(0, 500);
        var xAxis = d3.axisBottom(x);

        summaryCard.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(200, 200)")
            .call(xAxis);

    }

    function dataFilter(arr, filter) {
        var result = [];
        for (var element of arr) {
            if (/\d/.test(element.course_id) && !COURSES.has(element.course_id)) {
                COURSES.add(element.course_id)
                ALL_SCORES.push(parseFloat(element.score))
            }
            if (element.course_id == coursePicked && filter == "course") {
                result.push(element)
            } else if (element.course_id.match(/\D+/)[0].trim() == coursePicked.match(/\D+/)[0].trim() && filter == "course") {
                result.push(element)
            } else if (/^[a-zA-Z]+$/.test(element.course_id.trim()) && filter == "general") {
                result.push(element)
            }
        }
        return result;
    }

    function getPercentile(score) {
        var i = 0;
        score = parseFloat(score)

        ALL_SCORES.sort(function (a, b) {
            return a - b;
        });


        do {
            i += 1;
        } while (score > ALL_SCORES[i])

        return (i / ALL_SCORES.length) * 100
    }

    function getScore(percentile) {
        var i = 0;

        ALL_SCORES.sort(function (a, b) {
            return a - b;
        });

        do {
            i += 1;
        } while (percentile > ((i / ALL_SCORES.length) * 100))

        return ALL_SCORES[i];
    }

    d3.selection.prototype.moveToFront = function () {
        return this.each(function () {
            this.parentNode.appendChild(this);
        });
    };

    d3.selection.prototype.moveToBack = function () {
        return this.each(function () {
            var firstChild = this.parentNode.firstChild;
            if (firstChild) {
                this.parentNode.insertBefore(this, firstChild);
            }
        });
    };
})

