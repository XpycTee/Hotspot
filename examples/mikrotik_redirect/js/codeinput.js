document.addEventListener("DOMContentLoaded", function () {
	var codeInputs = document.querySelectorAll('.masked-code');
	
	var getInputNumbersValue = function (input) {
        // Return stripped input value — just numbers
        return input.value.replace(/\D/g, '');
    }
	
	var onCodeInput = function(e) {
		
		var input = e.target,
			inputNumbersValue = getInputNumbersValue(input);
			input.value = inputNumbersValue.substring(0, 4);
	}
	
	for (var codeInput of codeInputs) {
        codeInput.addEventListener('input', onCodeInput);
    }
});