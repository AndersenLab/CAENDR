# Genome Browser


<style>

.label {
  width: 80px;
  height: 18px;
  line-height: 12px;
  margin-bottom: 4px;
  display: inline-block;
}

.gt-3 {
    background-color: white;
    border: 1px dotted black;
    color: black;
}

.gt-0.PASS {
  background-color: rgba(194,194,214,1.0);
  border: 1px solid black;
  color: black;
}

.gt-2.PASS {
  background-color: rgba(0, 102, 255,1.0);
  border: 1px solid black;
  color: white;
}

.gt-0:not(.PASS) {
  background-color: rgba(194,194,214,0.25);
  border: 1px dotted black;
  color: black;
}

.gt-2:not(.PASS) {
  background-color: rgba(0, 102, 255,0.25);
  border: 1px dotted black;
  color: black;
}

.het {
  background-color: #ffff00;
  color: black;
}

.gt_set {
  border-right: 1px dotted #b3b3b3;
}

th {
  white-space: nowrap;
}

#variants {
  font-size: 12px;
}

</style>

<a name="standard-tracks"></a>
### Standard Tracks

The `Genes` and `Transcripts` tracks are displayed by default.

#### Genes 

Shows _C. elegans_ genes.

#### Transcripts

Shows transcripts of genes.

#### phyloP

The UCSC genome browser provides a [good explanation](https://genome.ucsc.edu/cgi-bin/hgTrackUi?db=hg19&g=cons46way) of the `phyloP` and `phastCons` tracks and how to interpret them.

phyloP (phylogenetic P-values) are designed to detect lineage-specific selection. Positive scores indicate conserved sites (slower evolution than expected under drift) whereas negative scores indicate acceleration (faster evolution than expected under drift).

* _Caenorhabditis elegans_
* _Caenorhabditis brenneri_
* _Caenorhabditis japonica_
* _Caenorhabditis remanei_
* _Caenorhabditis briggsae_
* _Strongyloides ratti_
* _Onchocerca volvulus_
* _Brugia malayi_

#### phastCons

phastCons scores range from 0-1 and represent the probability that each nucleotide belongs to a conserved element.

#### Transposons

The transposons track shows transposon calls from [Laricchia _et al._ 2017](https://andersenlab.org/publications/2017Laricchia.pdf). Each call lists the transposon type and __isotype__.

#### Divergent Regions

Hyper-divergent regions are genomic intervals that contain sequences not found in the N2 reference strain. They were identified by high levels of variation and low coverage from read alignments. For a complete description, please see [_Lee et al._ 2020](https://andersenlab.org/publications/2021LeeNatureEE.pdf).

Two divergent tracks are available:

* __Divergent Regions Summary__ - Divergent region intervals and their observed frequency across wild isolate strains.
* __Divergent Regions Strain__ - Divergent region intervals for individual strains.
