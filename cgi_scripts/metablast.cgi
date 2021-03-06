#!/usr/bin/perl

##################################################################################################
#
# This script borrows heavily from the EBI script here:
#
# http://www.ebi.ac.uk/Tools/webservices/download_clients/perl/soaplite/wublast_soaplite.pl
#
# we have taken out some uneccesary code, but plenty remains
# in and can be credited to EBI
#
##################################################################################################

# this script extracts sequence from the Meta4 database and
# uses the EBI weblast web-service to search for homologous 
# sequences.  The results are returned as a table

use CGI;
use DBI;
use HTML::Table;
use Bio::Seq;
use Bio::SeqIO;
use IO::String;
use SOAP::Lite;
use CGI;
use MIME::Base64;
use Bio::SearchIO;

# get the database credentials
require META4DB;

# create CGI object and print header
my $q = new CGI;
print $q->header, "\n";
print $q->start_html(-title => "Meta4blast", -style=>{'code'=>$META4DB::css});

# connect to the database
my $dbh = DBI->connect('DBI:mysql:' . $META4DB::dbname, $META4DB::dbuser, $META4DB::dbpass) || die "Could not connect to database: $DBI::errstr";

# get the assembly_id (aid) and gene name (gid)
my $aid = $q->param("aid");
my $gid = $q->param("gid");

# prepare and execute the SQL
my $sql = "select gp.gene_name, gp.gene_description, gp.protein_sequence
           from gene_prediction gp, contig c
           where gp.contig_id = c.contig_id and c.assembly_id = $aid and gp.gene_name = '$gid'";
$sth = $dbh->prepare($sql);
$sth->execute;

# get entire result set as an array
my @data = $sth->fetchrow_array;

# WSDL URL for service
my $WSDL = 'http://www.ebi.ac.uk/Tools/services/soap/wublast?wsdl';

# set the endpoint and name space for the service
my $serviceEndpoint = "http://www.ebi.ac.uk/Tools/services/soap/wublast";
my $serviceNamespace = "http://soap.jdispatcher.ebi.ac.uk";

# Create a service proxy from the WSDL. 
my $soap = SOAP::Lite->proxy($serviceEndpoint,	timeout => 6000)->uri($serviceNamespace);

# Default parameter values 
my %tool_params = ();
my %params = ();

# set blast parameters
$tool_params{'program'} = 'blastp';                                 # protein blast
$tool_params{'stype'} = 'protein';                                  # protein sequences
$tool_params{'sequence'} = ">$data[0] $data[1]\n$data[2]\n";        # the fasta formatted sequence

# set other parameters
$params{'email'} = 'test@server.com';                               # dummy e-mail: should change
$params{'database'} = 'uniprotkb_trembl';                           # search uniprot trembl
$params{'title'} = '$data[0]';                                      # use gene name as the title

# load a list of all possible databases
my (@dbList) = split /[ ,]/, $params{'database'};
	for ( my $i = 0 ; $i < scalar(@dbList) ; $i++ ) {
		$tool_params{'database'}[$i] =
		  SOAP::Data->type( 'string' => $dbList[$i] )->name('string');
	}

# run the job
my $jobid = &soap_run( $params{'email'}, $params{'title'}, \%tool_params );

# wait
sleep 1;

# poll the job status
my $jobStatus = 'PENDING';
while ( $jobStatus eq 'PENDING' || $jobStatus eq 'RUNNING' ) {
	sleep 5;    # Wait 5sec
	$jobStatus = soap_get_status($jobid);	
}

# if we get to here, the job has finished
# get the result
my $result = soap_get_result( $jobid, "out");

# create dummy filehandle using the text-output
# from the service and IO::String
my $fh = IO::String->new($result);

# create a Search::IO BioPerl object
my $in = Bio::SearchIO->new(-fh => $fh, -format => 'blast');

# create a table to store the output
my $tbl = new HTML::Table(-class=>'gene');
$tbl->addRow(("Hit","Description","Query Length","Hit Length","E value"));
$tbl->setRowHead(1);

# iterate over the BLAST results
while( my $result = $in->next_result ) {
  while( my $hit = $result->next_hit ) {
	my $name = $hit->name;
	$name =~ s/\S+:(\S+)/<a target="_blank" href="http:\/\/www.uniprot.org\/uniprot\/$1">$1<\/a>/;
	$tbl->addRow($name, $hit->description, $result->query_length, $hit->length, $hit->significance);
  }
}

$tbl->print;

$sth->finish;
$dbh->disconnect;
$q->end_html;


sub soap_get_result {
	my $jobid = shift;
	my $type  = shift;
	my $res = $soap->getResult(
		SOAP::Data->name( 'jobId' => $jobid )->attr( { 'xmlns' => '' } ),
		SOAP::Data->name( 'type'  => $type )->attr(  { 'xmlns' => '' } )
	);
	my $result = decode_base64( $res->valueof('//output') );
	return $result;
}

sub soap_get_status {
	my $jobid = shift;
	my $res = $soap->getStatus(
		SOAP::Data->name( 'jobId' => $jobid )->attr( { 'xmlns' => '' } ) );
	my $status_str = $res->valueof('//status');
	return $status_str;
}


sub soap_run {
	my $email  = shift;
	my $title  = shift;
	my $params = shift;
	if ( defined($title) ) {
	}

	my (@paramsList) = ();
	foreach my $key ( keys(%$params) ) {
		if ( defined( $params->{$key} ) && $params->{$key} ne '' ) {
			push @paramsList,
			  SOAP::Data->name( $key => $params->{$key} )
			  ->attr( { 'xmlns' => '' } );
		}
	}

	my $ret = $soap->run(
		SOAP::Data->name( 'email' => $email )->attr( { 'xmlns' => '' } ),
		SOAP::Data->name( 'title' => $title )->attr( { 'xmlns' => '' } ),	
		SOAP::Data->name( 'parameters' => \SOAP::Data->value(@paramsList) )
		  ->attr( { 'xmlns' => '' } )
	);
	return $ret->valueof('//jobId');
}










