/* Plot a set of data using a scatterplot with histograms along the axes.
 *
 * Adapted from https://gist.github.com/larsenmtl/b00fcedde4d3d37098509f514a354bac
 * Inspired by https://seaborn.pydata.org/generated/seaborn.jointplot.html
 */



/* Enum type mapping plot dimension names to corresponding indices. */
const PlotDimension = {
  'x_axis': 0,
  'y_axis': 1,
};



/* Helper function to compute the extent (the [min, max]) of a set of data,
 * plus a fixed "buffer" amount on either side.
 *
 * Equivalent to [min - buffer, max + buffer].
 * 
 * Arguments:
 *   - data (arr):   The list of data. See D3's implementation of `extent` for more details.
 *   - buffer (int): The amount to expand the range by.
 *   - f (function): A function to apply to each data point before using it to find the min or max.
 *                   See D3's implementation of `extent` for more details.
 */
function buffered_extent(data, buffer, f=null) {
  const r = d3.extent(data, f);
  r[0] -= buffer;
  r[1] += buffer;
  return r;
}



/* Add a histogram along an axis of a graph.
 *
 * Arguments:
 *   - d (int): The dimension of the histogram. 0 for x-axis, 1 for y-axis
 *   - axis: A d3 scaleLinear object mapping the domain of the given axis to its position in the graph
 *   - data: The data to plot
 *   - target: The SVG element to create the histogram in
 *   - config: Optional keyword arguments.
 */
function add_histogram_along_axis(d, axis, data, target, config={}) {

  // Validate the dimension parameter
  if (!(d === PlotDimension.x_axis || d === PlotDimension.y_axis)) {
    throw new RangeError(`The argument "d" must be a PlotDimension, but ${d} was given.`);
  }

  // Read values from config, filling in default values when not supplied
  const position     = config['position'] || [0, 0];
  const graph_height = config['height']   || 60;
  const color        = config['color']    || 'black';

  // Compute the approximate number of bins there should be
  let num_bins;
  if (config['bins_per_tick']) {
    num_bins = (axis.ticks().length - 1) * config['bins_per_tick']
  } else {
    const bin_width = config['bin_width'] || ((axis.ticks().length - 1) * 2)
    num_bins = (axis.domain()[1] - axis.domain()[0]) / bin_width;
  }

  // Get the x/y value for the provided dimension, plus the relative directions of the histogram
  // In this case, the "width" is along the main axis, and the "height" is the direction of the individual bars
  const [d_str, relative_width, relative_height] = [
    ['x', 'width', 'height'],
    ['y', 'height', 'width'],
  ][d];

  // Create a graph object for the histogram and transform it to lie on the appropriate axis
  const graph = target.append("g")
    .attr("transform", `translate(${ position[0] }, ${ position[1] })`);

  // Create the histogram bins
  const bins = d3.histogram()
    .domain(axis.domain())
    .thresholds(axis.ticks(num_bins))
    .value(n => n[d])
    (data);

  // Compute the size of the bin with the max value
  // This will be used to scale the histogram
  const max_bin_amount = d3.max(bins, n => n.length);

  // Linear scale from the value of a bin to its height on the page
  const bin_val_to_height = d3.scaleLinear().domain([0, max_bin_amount]).range([0, graph_height]);

  // Compute the "width" of a single bin, based on the start & end coords of the second bin
  // I use the second bin here in case the axis truncates in between ticks (i.e. isn't "niced"),
  // which would make the first bin a bit smaller
  const bin_width = Math.abs(axis(bins[1].x1) - axis(bins[1].x0)) - 1;

  // Fill each bar with the data from the appropriate bin,
  // and translate along the primary axis so they all sit next to one another
  const bar = graph.selectAll('.bar')
    .data(bins)
    .enter().append('g')
    .attr('class', 'bar')
    .attr('transform', function(n) {

      // D3 draws from top left, so along the x-axis,
      // offset the y-position of the bar based on the white space that should be above it
      if (d === PlotDimension.x_axis)
        return `translate(${ axis(n.x0) }, ${ bin_val_to_height(max_bin_amount - n.length) })`;

      // Along the y-axis, draw origin aligns with histogram base, so no x transformation necessary
      if (d === PlotDimension.y_axis)
        return `translate(${ 0 }, ${ axis(n.x1) })`;
    });

  // Create the rectangle for each bar
  bar.append('rect')
    .attr(d_str, 1)
    .attr(relative_width, bin_width)
    .attr(relative_height, n => bin_val_to_height(n.length))
    .style('fill', color);

  return bins;
}



/* Create a scatterplot with histograms along the x and y axes.
 *
 * Arguments:
 *   - container_selector: A selector for the element to create the graph in.
 *   - data: The data to graph.
 *   - config (dict): A set of optional parameters.  Values include:
 *       'margin'
 *       'hist_height'
 *       'width'
 *       'height'
 *       'bins_per_tick'
 *       'circle_radius'
 *       'fill_color'
 *       'stroke_color'
 *       'x_label'
 *       'y_label'
 */
function render_scatterplot_histograms(container_selector, data, config={}) {

    if (data.length == 0) {
      throw new Error('No data to plot')
    }

    // Get histogram heights from config
    const hist_height = config['hist_height'] || 60;

    // Set the dimensions and margins of the graph
    const margin = config['margin'] || {
      top:    48,
      right:  48,
      bottom: 48,
      left:   48,
    };
    const width  = (config['width']  || 600) - margin.left - margin.right;
    const height = (config['height'] || 400) - margin.top - margin.bottom;

    // Read values from config, filling in default values when not supplied
    const circle_radius = config['circle_radius'] || 8;
    const fill_color    = config['fill_color']    || 'black';
    const stroke_color  = config['stroke_color']  || 'none';
    const opacity       = config['opacity']       || 0;
    const opacity_hover = config['opacity_hover'] || 0;

    // Create a template function for the tooltip
    // By default, show label & value for each axis
    const tooltip_id       = config['tooltip_id']       || null;
    const tooltip_template = config['tooltip_template'] || ((d, labels) => `
      <p class="tooltip-body">${labels[0]}: ${d[0]}</p>
      <p class="tooltip-body">${labels[1]}: ${d[1]}</p>
    `);

    // Create the SVG object for the full graphic (scatterplot + histograms + margins)
    const svg = d3.select(container_selector).append('svg')
      //  .attr('width',  width  + margin.left + margin.right + hist_height)
      //  .attr('height', height + margin.top + margin.bottom + hist_height)
      .attr('width', "60%")
      .attr('height', "60%")
      .attr("viewBox", `0 0 800 900`)
      .attr('preserveAspectRatio','xMinYMin')

    // Add a graph element for the scatterplot
    const g = svg.append("g")
      .attr("transform", `translate(${ margin.left }, ${ margin.top + hist_height })`);

    // Create mapping functions from data set to coordinates in the scatterplot
    // Add a buffer of 0.1 in either direction so that dots aren't directly on graph edge
    //   The buffer has to be at least 0.1 bc of a quirk of the bin widths:
    //   the target width is 0.2, but the axis will round its ticks to the nearest 0.5,
    //   meaning there may be a gap of 0.1 on either end of either axis
    const x = d3.scaleLinear().domain(buffered_extent(data, 0.1, n => n[0])).range([0, width]).nice();
    const y = d3.scaleLinear().domain(buffered_extent(data, 0.1, n => n[1])).range([height, 0]).nice();

    // Add the x-axis
    g.append("g")
      .attr("transform", `translate(0, ${ height })`)
      .call(d3.axisBottom(x));

    // Add the y-axis
    g.append("g")
      .call(d3.axisLeft(y));

    // Add label for x-axis, if one is provided
    // Centered on scatterplot graph element
    if (config['x_label']) {
      svg.append('text')
        .attr('x', margin.left + (width / 2))
        .attr('y', height + margin.top + hist_height + 36)
        .attr('text-anchor', 'middle')
        .text(config['x_label'])
    }

    // Add label for y-axis, if one is provided
    // Centered on scatterplot graph element
    if (config['y_label']) {
      svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -(margin.top + hist_height + (height / 2)))
        .attr('y', 0)
        .attr('dy', '.75em')
        .attr('text-anchor', 'middle')
        .text(config['y_label'])

      }

    // Add the data points
    const dots = g.selectAll(".point")
      .data(data)
      .enter()
      .append("circle")
      .attr("cx", d => x(d[0]) )
      .attr("cy", d => y(d[1]) )
      .attr("r", circle_radius)
      .style('fill',    "#0719BC")
      // .style('stroke',  "black")
      // .style('stroke-width',  "1.5")
      .style('opacity', opacity)

    // Create tooltip for data point mouseover
    const tooltip = d3.select(container_selector)
      .append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    // If an ID is provided for the tooltip, add it
    if (tooltip_id) {
      tooltip.attr("id", tooltip_id);
    }

    // Add mouseover listener for individual dots
    dots.on('mouseover', function(d) {

      // Select the dot and grow its radius
      d3.select(this).attr('r', circle_radius + 2).style('opacity', opacity_hover);
      
      // Show the tooltip
      tooltip.html(tooltip_template(d, [ config['x_label'], config['y_label'] ]))
        .style('left', (d3.event.pageX + 10) + 'px') // Position tooltip to the right of the cursor
        .style('top',  (d3.event.pageY - 25) + 'px') // Position tooltip above the cursor
        .transition()
        .duration(200)
        .style('opacity', 1);
    });

    // Add mouseout event listener for individual dots
    dots.on('mouseout', function() {

      // Select the dot and restore its original radius
      d3.select(this).attr('r', circle_radius).style('opacity', opacity);

      // Hide the tooltip
      tooltip.transition()
        .duration(300)
        .style('opacity', 0);
    })


    // Gather the config params for the histograms
    const h_config = {
      height: hist_height,
      color: fill_color,
      bins_per_tick: config['bins_per_tick'],
      bin_width:     config['bin_width'],
    }

    // Add the two histograms
    add_histogram_along_axis(PlotDimension.x_axis, x, data, svg, {...h_config, position: [margin.left,         margin.top              ]})
    add_histogram_along_axis(PlotDimension.y_axis, y, data, svg, {...h_config, position: [margin.left + width, margin.top + hist_height]})
}



/* Create a histogram along the x axis.
 *
 * Arguments:
 *   - container_selector: A selector for the element to create the graph in.
 *   - data: The data to graph.
 *   - config (dict): A set of optional parameters.  Values include:
 *       'margin'
 *       'width'
 *       'height'
 *       'bins_per_tick'
 *       'fill_color'
 *       'x_label'
 */
function render_histogram(container_selector, data, config={}) {

  if (data.length == 0) {
    throw new Error('No data to plot')
  }

  // Set the dimensions and margins of the graph
  const margin = config['margin'] || {
    top:    48,
    right:  48,
    bottom: 48,
    left:   48,
  };
  const width  = (config['width']  || 600) - margin.left - margin.right;
  const height = (config['height'] || 400) - margin.top - margin.bottom;

  // Read values from config, filling in default values when not supplied
  const bins_per_tick = config['bins_per_tick'] || 1;
  const fill_color    = config['fill_color']    || 'black';

  // Create the SVG object for the full graphic (scatterplot + histograms + margins)
  const svg = d3.select(container_selector).append('svg')
    .attr('width',  width  + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)

  // Add a graph element for the scatterplot
  const g = svg.append("g")
    .attr("transform", `translate(${ margin.left }, ${ margin.top })`);

  // Create mapping functions from data set to coordinates in the scatterplot
  const x = d3.scaleLinear().domain(d3.extent(data, n => n[0])).range([0, width]).nice();

  // Add the x-axis
  g.append("g")
    .attr("transform", `translate(0, ${ height })`)
    .call(d3.axisBottom(x));

  // Add label for x-axis, if one is provided
  if (config['x_label']) {
    svg.append('text')
      .attr('x', margin.left + (width / 2))
      .attr('y', height + margin.top + 36)
      .attr('text-anchor', 'middle')
      .text(config['x_label'])
  }

  // Add the histogram
  const bins = add_histogram_along_axis(PlotDimension.x_axis, x, data, svg, {
    height: height,
    color: fill_color,
    bins_per_tick,
    position: [margin.left, margin.top ],
  });

  // Label the y-axis with "Count"
  const max_bin_amount = d3.max(bins, n => n.length);
  const yScale = d3.scaleLinear().domain([0, max_bin_amount]).range([margin.top + height, margin.top]).nice();
  const yAxis  = d3.axisLeft(yScale)
  svg.append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .call(yAxis);
  svg.append('text')
    .attr('transform', 'rotate(-90)')
    .attr('x', -(margin.top + (height / 2)))
    .attr('y', 0)
    .attr('dy', '.75em')
    .attr('text-anchor', 'middle')
    .text('Count')
}



/* Create a ranked bar plot.
 *
 * Arguments:
 *   - container_selector: A selector for the element to create the graph in.
 *   - data: The data to graph.
 *   - config (dict): A set of optional parameters.  Values include:
 *       'margin'
 *       'width'
 *       'height'
 *       'fill_color'
 *       'x_label'
 *       'y_label'
 */
function render_ranked_barplot(container_selector, data, config={}) {

  if (data.length == 0) {
    throw new Error('No data to plot')
  }

  // Set the dimensions and margins of the graph
  const margin = config['margin'] || {
    top:    48,
    right:  48,
    bottom: 48,
    left:   48,
  };
  const width  = (config['width']  || 600) - margin.left - margin.right;
  const height = (config['height'] || 400) - margin.top - margin.bottom;

  // Read values from config, filling in default values when not supplied
  const fill_color    = config['fill_color']    || 'black';

  // Create a template function for the tooltip
  // By default, show label & value for each axis
  const tooltip_id       = config['tooltip_id']       || null;
  const tooltip_template = config['tooltip_template'] || ((d) => `
    <p class="tooltip-body">${d[1]}: ${d[0]}</p>
  `);

  // Sort data
  data.sort(function(b, a) {
    return b[0] - a[0];
  });

  // Compute the range of the data
  // If both values are positive or both negative, set end of range to 0
  const data_range = d3.extent(data, d => d[0]);
  data_range[0] = Math.min(data_range[0], 0)
  data_range[1] = Math.max(data_range[1], 0)

  // Create the SVG object for the full graphic (scatterplot + histograms + margins)
  const svg = d3.select(container_selector).append('svg')
    .attr('width',  width  + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)

  // Create Y axis (map trait value to y coordinate)
  const yScale = d3.scaleLinear()
    .domain( data_range )
    .range([ height + margin.top, margin.top])
  const yAxis = d3.axisLeft(yScale)

  // Create X axis (map strain name to x coordinate)
  const xScale = d3.scaleBand()
    .domain(data.map( (d) => d[1] ))
    .range([ margin.left, margin.left + width ])
    .padding(0.05)
  const xAxis = d3.axisBottom(xScale)
    .tickFormat((d) => '')

  // Add the axes to the graph
  svg.append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .call(yAxis);
  svg.append("g")
    .attr("transform", "translate(0," + yScale(0) + ")")
    .call(xAxis)

  // Map a data point's absolute value to the corresponding bar height
  const bar_height = d3.scaleLinear()
    .domain([ 0, data_range[1] - data_range[0] ])
    .range([ 0, height ]);

  // Bars
  const bars = svg.selectAll("mybar")
    .data(data)
    .enter()
    .append("rect")
      .attr("x", (d) => xScale( d[1] ) )
      .attr("y", (d) => yScale( Math.max(d[0], 0) ) )
      .attr("width", xScale.bandwidth())
      .attr("height", (d) => bar_height( Math.abs(d[0]) ))
      .attr("fill", fill_color)

  // Create tooltip for bar mouseover
  const tooltip = d3.select(container_selector)
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

  // If an ID is provided for the tooltip, add it
  if (tooltip_id) {
    tooltip.attr("id", tooltip_id);
  }

  // Add mouseover listener for individual bars -- show the tooltip
  bars.on('mouseover', function(d) {
    tooltip.html(tooltip_template(d))
      .style('left', (d3.event.pageX + 10) + 'px') // Position tooltip to the right of the cursor
      .style('top',  (d3.event.pageY - 25) + 'px') // Position tooltip above the cursor
      .transition()
      .duration(200)
      .style('opacity', 1);
  });

  // Add mouseout event listener for individual bars -- hide the tooltip
  bars.on('mouseout', function() {
    tooltip.transition()
      .duration(300)
      .style('opacity', 0);
  })

  // Add label for y-axis, if one is provided
  if (config['y_label']) {
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(margin.top + (height / 2)))
      .attr('y', 0)
      .attr('dy', '.75em')
      .attr('text-anchor', 'middle')
      .text(config['y_label'])
    }
}
