//transform a numer in a {hour: h, minutes: m} data type
function calcTime(x) {
  var hours = Math.floor(x / 60);
  var minutes = x % 60;
  var str = "";
  if (hours == 0) {
    str += minutes + " minuti";
  } else if (hours == 1) {
    str += hours + " ora e " + minutes + " minuti";
  } else {
    str += hours + " ore e " + minutes + " minuti";
  }
  return str;
}
