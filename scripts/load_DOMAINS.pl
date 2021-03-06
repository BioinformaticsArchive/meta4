#!/usr/bin/perl

use strict;
use DBI;
use Getopt::Long;
use File::Basename;
use lib dirname(__FILE__);

# load the database access credentials
# should be in the same folder as the script
require META4DB;

# print out usage message
unless (@ARGV) {
	print "USAGE: perl load_DOMAINS.pl --domain_db_id <Domain DB ID> --file <File of domains>\n\n";
	print "Domain DB ID is required and should be the identifer of a domain database in the domain_db table\n";
	print "The file of domains is required.  This should be a plain text file, tab-delimited, with four columns: domain ID, domain Name, domain Length, domain description\n\n";
	print "EXAMPLE: perl load_DOMAINS.pl --domain_db_id 1 --file examples/domains_hit.txt\n";
	exit;
}

# get options from the command line
my $ddbid = undef;
my $file = undef;
GetOptions('domain_db_id=s' => \$ddbid, 'file=s' => \$file);

# check for valid options
unless (defined $ddbid) {
	warn "Must at least provide a domain DB ID\n";
	exit;
}
unless (defined $file && -f $file) {
	warn "Must at least provide a file and file must exist\n";
	exit;
}

# connect to the database
my $dbh = DBI->connect('DBI:mysql:' . $META4DB::dbname, $META4DB::dbuser, $META4DB::dbpass) || die "Could not connect to database: $DBI::errstr";

# iterate over the domains in $file
my $dcount = 0;
open(IN, $file) || die "Cannot open $file\n";
while(<IN>) {
	chomp();

	# split on tabs
	my($accn,$name,$len,$desc) = split(/\t/);

	# get rid of pesky ' characters which confuse MySQL
	$name =~ s/\'/prime /g;
	$desc =~ s/\'/prime /g;
	
	# insert into the database
	my $query = "INSERT INTO domain(domain_db_id, domain_accession, domain_name, domain_length, domain_description) values($ddbid,'$accn','$name',$len,'$desc')";
	$dbh->do($query) || die "Could not execute '$query': $DBI::errstr\n";
	$dcount++;

}
close IN;

# disconnect and print out message
$dbh->disconnect
    or warn "Disconnection failed: $DBI::errstr\n";
print "Inserted $dcount domains\n";
 
