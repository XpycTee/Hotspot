function doAjax(form) {
	$.ajax({
		url: 'http://10.10.0.51:8080/'+form[0].name,
		method: 'post',
		data: form.serialize(),
		success: function(response){
			if (response.status == 200) {
				document.sendin.username.value = response.data.username.value;
				document.sendin.password.value = response.data.password.value;
				document.sendin.submit();
				return false;
			} else if (response.status == 401) {
				$('form').hide()
				$('#login').css('display', 'flex');
			 } else if (response.status == 302) {
				$('form').hide()
				$('#code').val('')
				$('#auth').css('display', 'flex');
			} else {
				$('#error-message').html('<div class="mt-1" style="display: flex; position: absolute;"><div class="icon-alert"></div> <span style="font-size: 12px; line-height: 20px; color: rgb(235, 81, 95);">'+response.status_message+'</span></div>')
				$('form').hide()
				$('#login').css('display', 'flex');
				$('.login-input').addClass('error-input');
			}
		}
	});
}
$(document).ready(function(){
	$.mask.definitions['h'] = "[0|1|3|4|5|6|7|9]"
	$(".mask-code").mask("9999");
	
	doAjax($('#check'));
	$(".button").click(function(){
		form = $(this).parent()
		doAjax(form);
	});
});