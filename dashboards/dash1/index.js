/**
 * Name: Kobe Sarausad
 * Date: 2/8/2022
 * Section: AC
 *
 * This JavaScript file gives the data dashboard interactive abilities with different API calls
 * made based on different use input. These API calls are made on treasury.gov and alhpavantage.co.
 * Using the data retrieved from the API calls, it uses plotly to make interactive visuals.
 */
"use strict";
(function() {
  const BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service";
  const VANT_URL = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&outputsize=full&symbol=SPY&apikey=";
  const VANT_KEY = "0G1DKMS8B3H9RELN";
  const PARAMS = {
    "Debt to the Penny":
    {
      endpoint: "/v2/accounting/od/debt_to_penny",
      variable: "tot_pub_debt_out_amt",
      short: "public debt",
      fields: "record_date,tot_pub_debt_out_amt",
      filter: "",
      description: "Debt held by any entity outside of the United States federal government."
    },
    "Securities Issued":
    {
      endpoint: "/v1/accounting/od/securities_sales",
      variable: "gross_sales_amt",
      short: "treasury bills issued ($)",
      fields: "record_date,gross_sales_amt,security_class_desc",
      filter: "security_class_desc:eq:Bill,",
      description: "Dollar amount of treasury bills issued."
    }
  };

  window.addEventListener("load", init);

  /**
   * First adds the available selections to the variable menu and makes the default plots with a
   * 5 year date range. Then adds interactivity to the buttons so that whenever the user clicks
   * on the button, the plot will change.
   */
  function init() {
    addSelect();

    doCall();

    id("submit-btn").addEventListener("click", doCall);

    id("select").addEventListener("change", doCall);

    id("log").addEventListener("click", doCall);
  }

  /**
   * Adds the available selecitons to the page. This is so I am able to add variables later on
   * (if I want to).
   */
  function addSelect() {
    let options = Object.keys(PARAMS);

    for (let i = 0; i < options.length; i++) {
      let ele = gen("option");
      ele.setAttribute("value", options[i]);
      ele.textContent = options[i];
      id("select").appendChild(ele);
    }
  }

  /**
   * Makes the API call to both sites with the user inputted dates and variable.
   */
  function doCall() {
    let isDef = checkDef();

    let startDate = isDef[0];
    let endDate = isDef[1];

    if (endDate < startDate) {
      dateWrong();
    } else {
      let selected = id("select").value;

      let dates = "record_date:gte:" + startDate;

      let fullEndpoint = BASE_URL + PARAMS[selected]['endpoint'] + "?fields=";
      fullEndpoint += PARAMS[selected]['fields'] + "&filter=" + PARAMS[selected]['filter'];
      fullEndpoint += dates + "&limit=10000";

      let header = gen("h1");

      checkDef();
      header.textContent = id("select").value;

      getRequest(fullEndpoint, "fiscal");
      getRequest(VANT_URL + VANT_KEY, "stock");
    }
  }

  /**
   * Prints out useful message if the user inputted the start date that is later than the end date
   * or vice versa.
   */
  function dateWrong() {
    id("summary").innerHTML = "";
    let msg = gen("p");
    msg.textContent = "Enter correct dates! Make sure the end date comes after start date!";
    id("summary").appendChild(msg);
  }

  /**
   * Checks if the user just logged onto the site. If so, it will return today's date and the date
   * from 5 years ago from today.
   * @returns {Array} array of two dates
   */
  function checkDef() {
    let startDate;
    let endDate;

    if (id("start-date").value === id("end-date").value) {
      let today = new Date();
      endDate = today.toJSON().slice(0, 10);
      let year = endDate.slice(0, 4);
      startDate = endDate.replace(year, (parseInt(year) - 5).toString());
    } else {
      startDate = id("start-date").value;
      endDate = id("end-date").value;
    }

    return [startDate, endDate];
  }

  /**
   * Makes the API call to the sites. Catches any erorrs if there is an error.
   * @param {String} full - the URL of the API call with all the paramters.
   * @param {String} plot - indicator to which API to call.
   */
  async function getRequest(full, plot) {
    try {
      let res = await fetch(full);
      await statusCheck(res);
      let json = await res.json();

      if (plot === "fiscal") {
        makeFisc(json);
      } else if (plot === "stock") {
        makeStock(json);
      }
    } catch (error) {
      id("summary").innerHTML = "";
      let errorMsg = gen("p");
      let msg = "The inputted parameters returned an error!";
      msg += "Try again with different inputs!";
      errorMsg.textContent = msg;
      id("summary").appendChild(errorMsg);
    }
  }

  /**
   * From class: checks if the API call response is valid or not.
   * @param {Promise} response - the object containing the API call.
   * @returns {Promise} the response, error if the API call threw an error.
   */
  async function statusCheck(response) {
    if (!response.ok) {
      throw new Error(await response.text());
    }

    return response;
  }

  /**
   * Makes the plot given the dates, vals, and the tyep of plot (fiscal or stock). Then outputs the
   * plot onto the page.
   * @param {Array} dates - array of dates from the API calls
   * @param {Array} vals - array of the values from the API calls
   * @param {String} type - string representing which plot to output.
   */
  function makePlot(dates, vals, type) {
    let annot = {
      "fisc": [id("select").value, id("select").value, "Dollar Amount ($)", "fisc-plot"],
      "stock": ["SPY", "SPY (S&P 500 ETF)", "Price ($)", "stock-plot"]
    };
    let trace = {
      x: dates, y: vals,
      mode: "lines", name: annot[type][0],
      opacity: 0.8, sfill: 'tozeroy', line: {color: "#23515c", width: 1}
    };
    let layout = {
      title: {
        text: annot[type][1],
        font: {size: 24},
        xref: 'paper', x: 0.05
      },
      yaxis: {
        showgrid: false, type: log(), autorange: true,
        title: {text: annot[type][2], font: {size: 10, color: '#7f7f7f'}}
      }, xaxis: {
        showgrid: false,
        title: {text: "Date", font: {size: 10, color: '#7f7f7f'}}
      }
    };
    let data = [trace];
    Plotly.newPlot(annot[type][3], data, layout);
  }

  /**
   * Makes the plot for the stock.
   * @param {JSON} json - json returned from the stock API call
   */
  function makeStock(json) {
    let res = getRel(json["Time Series (Daily)"]);

    let dates = res[0];
    let vals = res[1];

    makePlot(dates, vals, "stock");
  }

  /**
   * Gets the values in the range of the dates the user inputted.
   * @param {JSON} json - full json returned from the API call.
   * @returns {Array} - array of the dates and values.
   */
  function getRel(json) {
    let isDef = checkDef();

    let startDate = isDef[0];
    let endDate = isDef[1];
    let keys = Object.keys(json);

    let dates = [];
    let vals = [];

    for (let i = 0; i < keys.length; i++) {
      if (keys[i] >= startDate && keys[i] <= endDate) {
        dates.push(keys[i]);
        vals.push(json[keys[i]]['4. close']);
      }
    }

    return [dates, vals];
  }

  /**
   * Makes the fiscal plot from the json returned from the treasury API call.
   * @param {JSON} json - json returned from treasury API call.
   */
  function makeFisc(json) {
    let jsonData = json.data;

    let dates = [];
    let vals = [];

    for (let i = 0; i < jsonData.length; i++) {
      if (jsonData[i]['record_date'] <= id("end-date").value) {
        dates.push(jsonData[i]['record_date']);
        vals.push(jsonData[i][PARAMS[id("select").value]['variable']]);
      }
    }

    makeSum(dates, vals);

    makePlot(dates, vals, "fisc");
  }

  /**
   * Indicator if the user wants a logged y-axis or not.
   * @returns {String} log if the user asked for logged y-axis, empty string otherwise.
   */
  function log() {
    if (id("log").checked) {
      return "log";
    }

    return "";
  }

  /**
   * Gets the percentage change between the inputted dates of the fiscal variable and adds this
   * summary into the page.
   * @param {Array} dates - dates between the range of the inputted dates.
   * @param {Array} vals - values corresponding to the dates.
   */
  function makeSum(dates, vals) {
    id("summary").innerHTML = "";

    let pct = (((vals[vals.length - 1] - vals[0]) / vals[0]) * 100).toFixed(2);

    let summary = gen("p");
    let desc = gen("p");
    let pctChg = gen("span");

    pctChg.textContent = pct + "%";

    if (pct > 100) {
      pctChg.style.opacity = (pct - 100) / 100;
      pctChg.style.color = "red";
    } else {
      pctChg.style.opacity = (100 - pct) / 100;
      pctChg.style.color = "green";
    }

    desc.textContent = "*" + PARAMS[id("select").value]['description'];
    desc.classList.add("desc");
    let sum = "Between " + dates[0] + " and " + dates[dates.length - 1];
    sum += " " + PARAMS[id("select").value]['short'] + " grew by ";
    summary.textContent = sum;
    summary.appendChild(pctChg);
    id("summary").appendChild(summary);
    id("summary").appendChild(desc);
  }

  /**
   * Returns a DOM element given an id.
   * @param {String} id - string that represents the id of interest
   * @return {DOM} DOM element with given id
   */
  function id(id) {
    return document.getElementById(id);
  }

  /**
   * Generates a DOM with specific id.
   * @param {String} id - string that represents the id of interest
   * @return {DOM} DOM with given id
   */
  function gen(id) {
    return document.createElement(id);
  }
})();
