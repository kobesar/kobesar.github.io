const margin = { top: 20, right: 20, bottom: 30, left: 40 };
const width = 500 - margin.left - margin.right;
const height = 300 - margin.top - margin.bottom;

var crimeTotalSvg = d3.select("#crime-pack")
  .append('svg')
  .attr('width', 500)
  .attr('height', 300);

  console.log('dafdsf')

d3.json("https://raw.githubusercontent.com/NSC508/Datathon2023/main/data/neighboryearoffensesum.json").then(function (data) {
  console.log(data)
  // const hierarchy = d3.hierarchy(data)
  //   .sum(d => d.n);

  // const pack = d3.pack()
  //   .size([svg.attr("width"), svg.attr("height")])
  //   .padding(5);

  // const nodes = svg.selectAll("circle")
  //   .data(rootNode.descendants())
  //   .join("circle")
  //   .attr("cx", d => d.x)
  //   .attr("cy", d => d.y)
  //   .attr("r", d => d.r)
  //   .attr("fill", "steelblue")
  //   .attr("cursor", "pointer")
  //   .on("click", d => console.log("Clicked", d.data.name));
})