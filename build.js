var projects = [
  {
    year: 2023,
    title: "Datathon: Seattle Crime",
    img: "images/profile.jpg"
  },
  {
    year: 2023,
    title: "Datathon: Seattle Crime 1",
    img: "images/profile.jpg"
  },
  {
    year: 2023,
    title: "Datathon: Seattle Crime 2",
    img: "images/profile.jpg"
  },
  {
    year: 2023,
    title: "Datathon: Seattle Crime 3",
    img: "images/profile.jpg"
  },
  {
    year: 2023,
    title: "Datathon: Seattle Crime 4",
    img: "images/profile.jpg"
  }
]

var projectSection = d3.select("#projects")

projectSection.selectAll(".card")
  .data(projects)
  .enter()
  .append("div")
  .html(
    (d) => {
      return `<img src="` + d.img + `"><span>` + d.title + `</span>`;
    }
  )
  .attr("class", "card")