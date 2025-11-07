function doAjax(form) {
		
	var request = new XMLHttpRequest();
	request.open('POST', '/' + form.name, true);
	//request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
	request.onload = function(){
		if (this.status >= 200 && this.status < 400) {
			var response = JSON.parse(this.response);
			if (response.status == 200) {
				document.sendin.username.value = response.data.username.value;
				document.sendin.password.value = response.data.password.value;
				document.sendin.submit();
				return false;
			} else if (response.status == 401) {
				form.style.display = 'none';
				login = document.getElementById('login');
				login.style.display = 'flex';
			} else if (response.status == 302) {
				form.style.display = 'none';
				code = document.getElementById('code');
				code.value = '';
				auth = document.getElementById('auth');
				auth.style.display = 'flex';
			} else {
				errMessage = document.getElementById('error-message');
				errMessage.innerHTML = '<div class="mt-1" style="display: flex; position: absolute;"><div class="icon-alert"></div> <span style="font-size: 12px; line-height: 20px; color: rgb(235, 81, 95);">'+response.status_message+'</span></div>';
				form.style.display = 'none';
				login = document.getElementById('login');
				login.style.display = 'flex';
				loginInputs = document.querySelectorAll('.login-input');
				for (var i = 0; i < loginInputs.length; i++) {
					loginInputs[i].classList.add('error-input');
				}
			}
		}
	}
	serializedForm = new FormData(form);
	request.send(serializedForm);
}

