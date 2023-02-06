'use strict';

(function () {
  window.addEventListener('load', init);

  const BTC = "https://blockchain.info/rawaddr/bc1qtdkvd5j89drlk2yaekpszm0rlrnsrfetdd5am7";
  const ETH = "https://api.etherscan.io/api?module=account&action=balance&address=0x97849c43DB2AD63905aCcAD01Cbd6794833A95b5&tag=latest&apikey=THDSMRJJ326TD6VI454YKW16VCZ65ATMD1"
  const BTC_PRICE = "https://blockchain.info/ticker"
  const ETH_PRICE = "https://api.etherscan.io/api?module=stats&action=ethprice&apikey=THDSMRJJ326TD6VI454YKW16VCZ65ATMD1"

  let data = {
    "BTC": {
      "amt": 0,
      "usd": 0,
    }, "ETH": {
      "amt": 0,
      "usd": 0,
    }
  };
  var chart;

  function init() {
    doCall();
    let n = new Date();
    document.getElementById("date").textContent = "BTC/ETH Prices Updated: " + n;
  }

  async function doCall() {
    await getRequest(BTC);
    await getRequest(BTC_PRICE);
    await getRequest(ETH);
    await getRequest(ETH_PRICE);
    makePlot();
  }

  async function getRequest(params) {
    try {
      let res = await fetch(params);

      await statusCheck(res);

      res = await res.json();

      handleResponse(res);
    } catch (err) {
      console.error(err);
    }
  }

  async function statusCheck(response) {
    if (!response.ok) {
      throw new Error(await response.text());
    }

    return response;
  }

  function handleResponse(res) {
    if (Object.keys(res).includes("txs")) {
      data["BTC"] = { "amt": res["final_balance"] / 100000000, "usd": 0 }
    } else if (Object.keys(res).includes("USD")) {
      data["BTC"]["usd"] = parseInt(res["USD"]["last"])
    } else if (Object.keys(res).includes("result") && Object.keys(res["result"]).includes("ethusd")) {
      data["ETH"]["usd"] = parseInt(res["result"]["ethusd"])
    } else if (Object.keys(res).includes("result")) {
      data["ETH"] = { "amt": Number(BigInt(res["result"]) / BigInt(1000000000000000000)), "usd": 0 }
    }
  }

  function makePlot() {
    var options = {
      series: [{
        data: [{
          x: "BTC", 
          y: data["BTC"]["amt"] * data["BTC"]["usd"],
          fillColor: "#f2a900"
        }, {
          x: "ETH",
          y: data["ETH"]["amt"] * data["ETH"]["usd"],
          fillcolor: "#a2bad2"
        }]
      }],
      chart: {
        type: 'bar',
        stacked: true,
        height: 350,
      },
      plotOptions: {
        bar: {
          borderRadius: 4,
          horizontal: false,
        }
      },
      dataLabels: {
        enabled: false
      },
      xaxis: {
        categories: ['BTC', 'ETH'],
      }
    };

    chart = new ApexCharts(document.getElementById("plot"), options);
    chart.render();
  }

  function makeETH(res) {
    chart.appendData([{
      data: [BigInt(res["result"]) / BigInt(1000000000000000000)]
    }]);
    // var options = {
    //   series: [{
    //   data: [res["result"] / 1000000000000000000n]
    // }],
    //   chart: {
    //   type: 'bar',
    //   height: 350,
    // },
    // fill: {
    //   colors: ['#a2bad2']
    // },
    // plotOptions: {
    //   bar: {
    //     borderRadius: 4,
    //     horizontal: false,
    //   }
    // },
    // dataLabels: {
    //   enabled: false
    // },
    // xaxis: {
    //   categories: ['BTC'],
    // }
    // };

    // var chart = new ApexCharts(document.getElementById("plot"), options);
  }

  function makeBTC(res) {
    var options = {
      series: [{
        data: [res["final_balance"] / 100000000]
      }],
      chart: {
        type: 'bar',
        height: 350,
      },
      fill: {
        colors: ['#f2a900', '#a2bad2']
      },
      plotOptions: {
        bar: {
          borderRadius: 4,
          horizontal: false,
        }
      },
      dataLabels: {
        enabled: false
      },
      xaxis: {
        categories: ['BTC', 'ETH'],
      }
    };

    chart = new ApexCharts(document.getElementById("plot"), options);
    chart.render();

    getRequest(ETH);
  }

})();