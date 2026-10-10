#!/usr/bin/perl
# Minimal read-only HTTP server for the 진척판: serves <dir>/index.html for any GET path.
# Uses only core Perl, which every macOS ships (python3 there may be an install-prompt shim).
# Usage: serve_page.pl <dir> <port>
use strict; use warnings; use IO::Socket::INET;
my ($dir, $port) = @ARGV;
my $srv = IO::Socket::INET->new(LocalAddr => '0.0.0.0', LocalPort => $port, Listen => 16, ReuseAddr => 1) or die "listen $port: $!";
$SIG{PIPE} = 'IGNORE';
while (my $c = $srv->accept) {
    $c->timeout(10);
    my $line = <$c> // ''; while (my $h = <$c>) { last if $h =~ /^\r?\n$/ }
    my ($method) = $line =~ /^(\S+)/;
    if (!$method || ($method ne 'GET' && $method ne 'HEAD')) { print $c "HTTP/1.0 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n"; close $c; next }
    my $body = '';
    if (open my $f, '<:raw', "$dir/index.html") { local $/; $body = <$f>; close $f }
    print $c "HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-cache\r\nContent-Length: " . length($body) . "\r\n\r\n";
    print $c $body if $method eq 'GET';
    close $c;
}
