function scroller(){
  let container = d3.select('body')
  let dispatch = d3.dispatch('active', 'progress');
  let sections = d3.selectAll('.step')
  let sectionPositions
  let currentIndex = -1
  let containerStart = 0;
// Binds the position function to the scroll event, and the resize function to the resize event. What these functions do are detailed below. 
  function scroll(){
    d3.select(window)
      .on('scroll.scroller', position)
      .on('resize.scroller', resize)
      resize();
    let timer = d3.timer(function() {
      position();
      timer.stop();
    });
  }
//The resize function determines where each of the .step elements are on the page, relative to the top of the first element. It saves all of the co-ordinates of these elements in an array called sectionPositions
  function resize(){
    sectionPositions = [];
    let startPos;
    sections.each(function(d, i) {
      let top = this.getBoundingClientRect().top;
      if (i === 0 ){
        startPos = top;
      }
      sectionPositions.push(top - startPos)
    });
  }
//The position function determines where the user is on the page (using window.pageYOffset), and uses that to determine which section of text should currently be in view. It then uses D3’s dispatching tools to signal the 'progress' event, which will be used in the main script, passing along the current section index so that the script knows which stage of the animation/visualisation should be showing. 
  function position() {
    let pos = window.pageYOffset - 300 - containerStart;
    let sectionIndex = d3.bisect(sectionPositions, pos);
    sectionIndex = Math.min(sections.size()-1, sectionIndex);
    if (currentIndex !== sectionIndex){
      dispatch.call('active', this, sectionIndex);
      currentIndex = sectionIndex;
    }
    let prevIndex = Math.max(sectionIndex - 1, 0);
    let prevTop = sectionPositions[prevIndex]
    let progress = (pos - prevTop) / (sectionPositions[sectionIndex]   - prevTop);
    dispatch.call('progress', this, currentIndex, progress)
  }
//The code here adds an event listener to the dispatcher.
  scroll.container = function(value) {
    if (arguments.legth === 0){
      return container
    }
    container = value
    return scroll
  }
  scroll.on = function(action, callback){
    dispatch.on(action, callback)
  };
  return scroll;
}