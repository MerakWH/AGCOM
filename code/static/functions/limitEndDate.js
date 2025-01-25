async function limitEndDate() {
  end_date.min = start_date.value;
  if (
    Number(end_date.value.split("-")[0]) <
      Number(start_date.value.split("-")[0]) ||
    (Number(end_date.value.split("-")[0]) ==
      Number(start_date.value.split("-")[0]) &&
      Number(end_date.value.split("-")[1]) <
        Number(start_date.value.split("-")[1])) ||
    (Number(end_date.value.split("-")[1]) ==
      Number(start_date.value.split("-")[1]) &&
      Number(end_date.value.split("-")[2]) <
        Number(start_date.value.split("-")[2]))
  ) {
    end_date.value = start_date.value;
  }
}
