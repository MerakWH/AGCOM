//function to feetch data from python APIs
async function fetchData(url) {
  if (controller.signal.aborted) return null;                   //if controller is aborted block fetch
  try {
    const response = await fetch(url, {
      signal: controller.signal                                 //while fetching, check if controller gets aborted
    });
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();
    return data;                                                //return fetched values
  } catch (error) {
    if (error.name === "AbortError") {                          //if fetch gets aborted (don't do anything)
    } else {
      console.error("Errore nel recupero dei dati:", error);
    }
    return null;
  }
}

// fetch topics array (for TOPICS constant global variable)
async function fetchTopicsArray() {
  const data = await fetchData(`/v1/topics`);
  return data.topics;
}