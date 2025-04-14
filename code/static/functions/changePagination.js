async function analisiPolitico() {
    paginationLinks.forEach(l => l.classList.remove('active'));
    document.getElementById("theActiveOne").classList.add('active')
    document.getElementById("analisiPolitico").style.display = "inline-block";
    document.getElementById("confrontoPolitici").style.display = "none";
    document.getElementById("analisiCanale").style.display = "none";
    document.getElementById("analisiProgramma").style.display = "none";
}

async function confrontoPolitici() {
    paginationLinks.forEach(l => l.classList.remove('active'));
    document.getElementById("theActiveTwo").classList.add('active')
    document.getElementById("analisiPolitico").style.display = "none";
    document.getElementById("confrontoPolitici").style.display = "inline-block";
    document.getElementById("analisiCanale").style.display = "none";
    document.getElementById("analisiProgramma").style.display = "none";
}

async function analisiCanale() {
    paginationLinks.forEach(l => l.classList.remove('active'));
    document.getElementById("theActiveThree").classList.add('active')
    document.getElementById("analisiPolitico").style.display = "none";
    document.getElementById("confrontoPolitici").style.display = "none";
    document.getElementById("analisiCanale").style.display = "inline-block";
    document.getElementById("analisiProgramma").style.display = "none";
}

async function analisiProgramma() {
    paginationLinks.forEach(l => l.classList.remove('active'));
    document.getElementById("theActiveFour").classList.add('active')
    document.getElementById("analisiPolitico").style.display = "none";
    document.getElementById("confrontoPolitici").style.display = "none";
    document.getElementById("analisiCanale").style.display = "none";
    document.getElementById("analisiProgramma").style.display = "inline-block";
}