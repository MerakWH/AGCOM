// change checkbox type

async function changeType() {
  const news = document.getElementById("news");
  const speech = document.getElementById("speech");
  if (news.checked == true && speech.checked == true) {
    cb = "both";
  } else if (news.checked == true) {
    cb = "news";
  } else if (speech.checked == true) {
    cb = "speech";
  } else {
    cb = "none";
  }
}
