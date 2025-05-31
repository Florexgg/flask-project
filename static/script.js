let answers = [0, 0, 0];

function answer(index, isCorrect) {
  answers[index] = isCorrect ? 1 : 0;
}

function submitTest() {
  fetch('/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers: answers })
  })
  .then(response => response.json())
  .then(data => {
    document.getElementById("result").innerText = data.result;
  });
}
