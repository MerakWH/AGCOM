async function fetchData(url) {
  if (controller.signal.aborted) return null;
  try {
    const response = await fetch(url, {
      signal: controller.signal
    });
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
    } else {
      console.error("Errore nel recupero dei dati:", error);
    }
    return null;
  }
}

// fetch topics
async function fetchTopics() {
  var topics = [];
  i = 1;
  while (true) {
    const data = await fetchData(`/v1/topics?page=${i}`);
    i++;
    if (data.topics.length === 0) {
      break;
    }
    data["topics"].forEach((val) => {
      topics.push(val);
    });
  }
  return topics;
}
