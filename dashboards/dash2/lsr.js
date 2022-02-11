`use strict`;
(function () {
  window.addEventListener("load", init);

  let randoms = [[], []];
  let predResids = [[], []];
  // let MULT = [1, 2, 0.5];

  function init() {
    var trace = {
      x: [],
      y: [],
      mode: 'markers',
      type: 'scatter'
    };

    var layout = {
      plot_bgcolor: '#081D57',
      paper_bgcolor: '#081D57'
    };

    var data = [trace];

    Plotly.newPlot('scatter', data, layout);

    document.getElementById("slope").addEventListener("click", changeSlope);
    document.getElementById("n").addEventListener("click", function() {
      createRandom();
      changeSlope();
    });

    // document.getElementById("int").addEventListener("click", function() {
    //   addInt();
    //   changeSlope();
    // });
  }

  function addInt() {
    for (let i = 0; i < predResids[1].length; i++) {
      predResids[1][i] += parseInt(document.getElementById("int").value);
    }
  }

  function changeSlope() {
    let slope = document.getElementById("slope").value;
    for (let i = 0; i < predResids[0].length; i++) {
      predResids[1][i] = Math.pow((slope * predResids[0][i]) - randoms[1][i], 2);
    }

    document.getElementById("slope-num").textContent = slope;
    document.getElementById("n-num").textContent = document.getElementById("n").value;

    var line = {
      x: [0, 10],
      y: [0, slope * 10],
      mode: 'lines',
      type: 'scatter',
      marker: {
        color: '#03DAC6',
        opacity: 0.7
      }
    };

    var points = {
      x: randoms[0],
      y: randoms[1],
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: '#BB86FC',
        opacity: 0.5,
      }
    }

    var layout = {
      plot_bgcolor: '#081D57',
      paper_bgcolor: '#081D57'
    };

    var data = [line, points];

    console.log(predResids);
    console.log(randoms);

    document.getElementById("resid").textContent = getMean(predResids[1]).toFixed();

    Plotly.newPlot('scatter', data, layout);
  }

  function createRandom() {
    randoms = [[], []];
    for (let i = 0; i < document.getElementById("n").value; i++) {
      randoms[0].push(Math.random() * 10);
      randoms[1].push((randoms[0][i] + Math.random()) * 10);
    }

    predResids[0] = randoms[0];
  }

  function getMean(arr) {
    let sum = 0;
    for (let i = 0; i < arr.length; i++) {
      sum += arr[i];
    }

    return sum / arr.length;
  }

  function getRandomIntInclusive(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min + 1) + min);
  }
})();