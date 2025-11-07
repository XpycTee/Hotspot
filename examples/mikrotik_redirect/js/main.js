function ready(fn) {
  if (document.readyState != 'loading'){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

ready(function(){
	checkForm = document.getElementById('check');
	doAjax(checkForm);
	buttons = document.querySelectorAll('.button');
	for (var i = 0; i < buttons.length; i++) {
		buttons[i].addEventListener('click', function () {form = this.parentNode; doAjax(form);}, false);
	}
});