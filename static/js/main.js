$(document).ready(function () {
  	var hours = new Date().getHours();

  	if(hours > 6 && hours < 8){
  		$('body').css('background', '#D5F9FF');
  	}
  	if(hours >= 8 && hours < 17){
  		$('body').css('background', '#67A5CC');
  	}
  	if(hours >= 17 && hours <= 20){
  		$('body').css('background', '#c98344');
  	}
	if(hours >= 21){
  		$('body').css('background', '#645b8d');
  	}
});
