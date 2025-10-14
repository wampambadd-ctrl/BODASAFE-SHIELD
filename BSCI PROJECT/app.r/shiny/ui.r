# ui.R
library(shiny)
fluidPage(
  titlePanel("BodaSafe Shield Quote Tool"),
  sidebarLayout(
    sidebarPanel(
      numericInput("lat", "Latitude:", 0.3476),
      numericInput("lon", "Longitude:", 32.5825),
      sliderInput("hours", "Daily Hours:", 1, 12, value=8)
    ),
    mainPanel(
      textOutput("premium_text")
    )
  )
)

